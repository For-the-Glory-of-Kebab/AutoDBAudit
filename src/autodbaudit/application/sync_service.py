"""
Sync Service - Thin Orchestrator for Sync Operations.

This is the main entry point for --sync command.
It orchestrates the sync process but delegates all logic to specialized modules.

Architecture Note:
    - This file should stay around 150-200 lines
    - All diffing logic is in application/diff/
    - All action handling is in application/actions/
    - All stats are from StatsService
    - State machine is in domain/
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

from autodbaudit.infrastructure.sqlite import HistoryStore
from autodbaudit.infrastructure.excel import EnhancedReportWriter

# Domain types
from autodbaudit.domain.change_types import SyncStats

# Application services
from autodbaudit.application.stats_service import StatsService, format_cli_stats
from autodbaudit.application.diff.findings_diff import diff_findings, get_exception_keys
from autodbaudit.application.actions.action_detector import (
    detect_all_actions,
    consolidate_actions,
)
from autodbaudit.application.actions.action_recorder import ActionRecorder

if TYPE_CHECKING:
    from autodbaudit.application.audit_service import AuditService

logger = logging.getLogger(__name__)

# CLI Colors
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"


class SyncService:
    """
    Orchestrator for sync operations.

    This class coordinates the sync workflow but delegates
    all logic to specialized modules.

    Workflow:
    1. Pre-flight checks (finalized state, etc.)
    2. Read annotations from Excel
    3. Re-audit current state
    4. Diff findings (baseline vs current)
    5. Detect all actions
    6. Record actions (with deduplication)
    7. Calculate stats (single source)
    8. Write Excel report
    """

    def __init__(self, db_path: str | Path = "output/audit_history.db"):
        """Initialize sync service."""
        self.db_path = Path(db_path)

        # Validation: Sync cannot run without an existing audit database
        if not self.db_path.exists():
            # If the DB doesn't exist, we can't sync.
            # We raise a specific error that the CLI can catch or just exit cleanly.
            # The user specifically requested "sync command without an audit shouldn't create a db"
            raise FileNotFoundError(
                f"No active audit found at {self.db_path}. Run 'audit' command first."
            )

        self.store = HistoryStore(self.db_path)
        self.store.initialize_schema()
        logger.info("SyncService initialized")

    @property
    def conn(self):
        """Get database connection for legacy compatibility."""
        return self.store._get_connection()

    def get_initial_run_id(self) -> int | None:
        """Get the first (baseline) audit run ID."""
        return self.store.get_initial_baseline_id()

    def get_latest_run_id(self) -> int | None:
        """Get the most recent audit run ID."""
        return self.store.get_latest_run_id()

    def sync(
        self,
        audit_service: "AuditService" = None,
        targets_file: str | None = "sql_targets.json",
        audit_manager: Any = None,
        audit_id: int | None = None,
    ) -> dict:
        """
        Execute sync operation.

        Returns dict with status, stats, and report path.
        """
        # ─────────────────────────────────────────────────────────────
        # PHASE 1: Pre-flight Checks
        # ─────────────────────────────────────────────────────────────
        initial_run_id = self.get_initial_run_id()
        if initial_run_id is None:
            logger.error("No baseline audit found. Run --audit first.")
            return {"error": "No baseline audit found"}

        run = self.store.get_audit_run(initial_run_id)
        if run and run.status == "finalized":
            msg = f"Audit #{initial_run_id} is FINALIZED. Sync blocked."
            logger.error(msg)
            print(f"\n{RED}⛔ {msg}{RESET}")
            return {"error": "Audit is finalized"}

        # Resolve paths
        if audit_manager and audit_id:
            output_dir = audit_manager._get_audit_folder(audit_id)
            input_excel = audit_manager.get_latest_excel_path(audit_id)
            final_excel = input_excel
        else:
            output_dir = self.db_path.parent
            input_excel = self.db_path.parent / "Audit_Latest.xlsx"
            final_excel = input_excel

        logger.info("Sync: baseline run ID = %d", initial_run_id)

        # Check if Excel file is locked (open in Excel)
        if input_excel and input_excel.exists():
            try:
                with open(input_excel, "r+b"):
                    pass  # File is not locked
            except PermissionError:
                msg = f"Excel file is open: {input_excel.name}. Please close it and retry."
                logger.error(msg)
                print(f"\n{RED}⛔ {msg}{RESET}")
                return {"error": "Excel file is locked"}

        # ─────────────────────────────────────────────────────────────
        # PHASE 2: Read Annotations from Excel
        # ─────────────────────────────────────────────────────────────
        from autodbaudit.application.annotation_sync import AnnotationSyncService

        annot_sync = AnnotationSyncService(self.db_path)
        old_annotations = {}
        current_annotations = {}
        # NOTE: exception_changes will be populated in Phase 4 after re-audit

        if input_excel and input_excel.exists():
            logger.info("Reading annotations from %s", input_excel)
            old_annotations = annot_sync.load_from_db()
            current_annotations = annot_sync.read_all_from_excel(input_excel)
            annot_sync.persist_to_db(current_annotations)
            # Exception detection moved to Phase 4 where we have current findings

            # Debug: Count annotations by entity type
            old_by_type = {}
            for k in old_annotations:
                etype = k.split("|")[0] if "|" in k else "unknown"
                old_by_type[etype] = old_by_type.get(etype, 0) + 1

            new_by_type = {}
            for k in current_annotations:
                etype = k.split("|")[0] if "|" in k else "unknown"
                new_by_type[etype] = new_by_type.get(etype, 0) + 1

            logger.info("Annotations from DB: %s", old_by_type)
            logger.info("Annotations from Excel: %s", new_by_type)

        try:
            # ─────────────────────────────────────────────────────────────
            # PHASE 3: Run Re-Audit
            # ─────────────────────────────────────────────────────────────
            logger.info("Running re-audit...")

            if audit_service is None:
                from autodbaudit.application.audit_service import AuditService

                audit_service = AuditService(
                    config_dir=Path("config"), output_dir=Path("output")
                )

            # Prepare writer
            writer = EnhancedReportWriter()
            baseline_org = run.organization if run else "Unspecified"
            baseline_started = run.started_at if run else datetime.now()

            writer.set_audit_info(
                run_id=initial_run_id,
                organization=baseline_org,
                audit_name="Remediation Sync Report",
                started_at=baseline_started,
            )

            try:
                processed_writer = audit_service.run_audit(
                    targets_file=targets_file, writer=writer, skip_save=True
                )
            except Exception as e:
                logger.error("Re-audit failed: %s", e)
                # Note: run_audit might have created a run ID. We need to check finding it.
                # However, audit_service doesn't easily expose it if it crashes mid-flight.
                # We relying on get_latest_run_id to find the zombie run.

                # Check if a new run was actually created
                zombie_id = self.get_latest_run_id()
                if zombie_id and zombie_id > initial_run_id:
                    self.store.fail_audit_run(zombie_id, f"Audit Crash: {e}")

                return {"error": f"Re-audit failed: {e}"}

            current_run_id = self.get_latest_run_id()
            if not current_run_id:
                return {"error": "Re-audit did not produce a run ID"}

            if current_run_id != initial_run_id:
                self.store.mark_run_as_sync(current_run_id)

            # ─────────────────────────────────────────────────────────────
            # PHASE 4: Diff Findings
            # ─────────────────────────────────────────────────────────────
            baseline_findings = self.store.get_findings(initial_run_id)
            current_findings = self.store.get_findings(current_run_id)

            # Get valid instances
            valid_pairs = self.store.get_instances_for_run(current_run_id)
            valid_keys = {
                f"{s.hostname}|{i.instance_name or ''}".lower() for s, i in valid_pairs
            }

            # Get exception keys
            old_exception_keys = get_exception_keys(baseline_findings, old_annotations)
            new_exception_keys = get_exception_keys(
                current_findings, current_annotations
            )

            # Perform diff
            findings_diff = diff_findings(
                old_findings=baseline_findings,
                new_findings=current_findings,
                old_exceptions=old_exception_keys,
                new_exceptions=new_exception_keys,
                valid_instance_keys=valid_keys,
            )

            # ─────────────────────────────────────────────────────────────
            # PHASE 4b: Detect Exception Changes (using current findings for status)
            # ─────────────────────────────────────────────────────────────
            exception_changes = []
            if current_annotations:
                raw_exceptions = annot_sync.detect_exception_changes(
                    old_annotations, current_annotations, current_findings
                )

                logger.info(
                    "Exception changes detected: %d (types: %s)",
                    len(raw_exceptions),
                    (
                        {ex.get("entity_type", "?") for ex in raw_exceptions}
                        if raw_exceptions
                        else set()
                    ),
                )

                # Convert to DetectedChange objects
                from autodbaudit.application.actions.action_detector import (
                    create_exception_action,
                )
                from autodbaudit.domain.change_types import ChangeType
                from autodbaudit.infrastructure.sqlite.schema import set_annotation
                import sqlite3

                conn = sqlite3.connect(str(self.db_path))
                conn.row_factory = sqlite3.Row

                for ex in raw_exceptions:
                    change_type = ex.get("change_type", "added")
                    ct = ChangeType.EXCEPTION_ADDED
                    if change_type == "removed":
                        ct = ChangeType.EXCEPTION_REMOVED
                        # CRITICAL: Explicitly clear old annotation's review_status
                        # This handles key mismatch (legacy vs UUID)
                        full_key = ex["full_key"]
                        parts = full_key.split("|", 1)
                        if len(parts) == 2:
                            etype, ekey = parts
                            set_annotation(
                                connection=conn,
                                entity_type=etype,
                                entity_key=ekey,
                                field_name="review_status",
                                field_value="",  # Clear it
                            )
                            logger.info("Cleared review_status for %s", full_key[:60])
                    elif change_type == "updated":
                        ct = ChangeType.EXCEPTION_UPDATED

                    exception_changes.append(
                        create_exception_action(
                            entity_key=ex["full_key"],
                            justification=ex.get("justification", ""),
                            change_type=ct,
                            entity_type=ex.get("entity_type"),  # Pass explicitly
                        )
                    )

                conn.close()

            # ─────────────────────────────────────────────────────────────
            # PHASE 5: Detect & Record Actions
            # ─────────────────────────────────────────────────────────────
            all_actions = detect_all_actions(
                findings_diff=findings_diff,
                exception_changes=exception_changes,
            )

            # Consolidate (apply priority rules)
            consolidated = consolidate_actions(all_actions)

            # Record to database
            recorder = ActionRecorder(self.store)
            recorded = recorder.record_actions(
                actions=consolidated,
                initial_run_id=initial_run_id,
                sync_run_id=current_run_id,
            )

            logger.info("Recorded %d actions", recorded)

            # ─────────────────────────────────────────────────────────────
            # PHASE 6: Calculate Stats
            # ─────────────────────────────────────────────────────────────
            prev_run_id = self.store.get_previous_sync_run(current_run_id)

            stats_service = StatsService(
                findings_provider=self.store,
                annotations_provider=annot_sync,
            )

            stats = stats_service.calculate(
                baseline_run_id=initial_run_id,
                current_run_id=current_run_id,
                previous_run_id=prev_run_id,
            )

            # ─────────────────────────────────────────────────────────────
            # PHASE 7: Write Excel Report
            # ─────────────────────────────────────────────────────────────
            # Set Cover sheet stats from StatsService (unified source of truth)
            if hasattr(processed_writer, "set_stats_from_service"):
                processed_writer.set_stats_from_service(
                    active_issues=stats.active_issues,
                    documented_exceptions=stats.documented_exceptions,
                    compliant_items=stats.compliant_items,
                    # Granular stats (Change Stats)
                    fixed=stats.fixed_since_last,
                    regressed=stats.regressions_since_last,
                    new_issues=stats.new_issues_since_last,
                    docs_changed=(
                        stats.docs_added_since_last
                        + stats.docs_updated_since_last
                        + stats.docs_removed_since_last
                    ),
                    exceptions_changed=(
                        stats.exceptions_added_since_last
                        + stats.exceptions_removed_since_last
                        + stats.exceptions_updated_since_last
                    ),
                )

            # Add actions to writer
            formatted_actions = recorder.get_formatted_actions(initial_run_id)
            for action in formatted_actions:
                writer.add_action(
                    server_name=action["server"],
                    instance_name=action["instance"],
                    category=action["category"],
                    finding=action["finding"],
                    risk_level=action["risk_level"],
                    recommendation=action["description"],
                    status=action["status"],
                    found_date=action["detected_date"],
                    notes=action.get("notes", ""),
                    action_id=action.get("id"),
                )

            # Save report
            if hasattr(processed_writer, "save"):
                processed_writer.save(final_excel)

            # Write annotations back
            latest_annotations = annot_sync.load_from_db()
            annot_sync.write_all_to_excel(final_excel, latest_annotations)

            logger.info("Sync complete. Report: %s", final_excel)

            # ─────────────────────────────────────────────────────────────
            # Return Result
            # ─────────────────────────────────────────────────────────────
            return {
                "status": "success",
                "initial_run_id": initial_run_id,
                "current_run_id": current_run_id,
                "stats": stats.to_dict(),
                "stats_obj": stats,  # Return object for CLI renderer
                "report_path": str(final_excel),
                "actions_recorded": recorded,
                # Legacy compatibility fields
                "exceptions": stats.exceptions_added_since_last,
                "total_exceptions": stats.documented_exceptions,
                "baseline": {
                    "fixed": stats.fixed_since_baseline,
                    "still_failing": stats.active_issues,
                    "regression": stats.regressions_since_baseline,
                    "new": stats.new_issues_since_baseline,
                },
                "recent": {
                    "fixed": stats.fixed_since_last,
                    "still_failing": stats.active_issues,
                    "regression": stats.regressions_since_last,
                    "new": stats.new_issues_since_last,
                },
            }
        except KeyboardInterrupt:
            logger.warning("Sync Interrupted by User")
            # Try to fail the run if one was created
            possible_run = self.store.get_latest_run_id(include_failed=True)
            if possible_run and possible_run > initial_run_id:
                self.store.fail_audit_run(possible_run, "Interrupted by User")
            return {"error": "Sync interrupted"}

        except Exception as e:
            logger.exception("Sync Critical Failure")
            possible_run = self.store.get_latest_run_id(include_failed=True)
            if possible_run and possible_run > initial_run_id:
                self.store.fail_audit_run(possible_run, f"Critical Failure: {str(e)}")
            return {"error": f"Sync failed: {e}"}
