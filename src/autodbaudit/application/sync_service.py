"""
Sync service for tracking remediation progress.

Core principle: action_log records fixes with REAL timestamps.

Flow:
1. Re-audit current state
2. Diff against INITIAL baseline (not previous sync)
3. For NEW fixes: record with today's timestamp
4. For EXISTING fixes: preserve original timestamp
5. Update action_log with current sync run ID
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autodbaudit.infrastructure.sqlite import HistoryStore
from autodbaudit.infrastructure.excel import EnhancedReportWriter
from autodbaudit.application.audit_service import AuditService

logger = logging.getLogger(__name__)

# Colors for CLI output
RED = "\033[91m"
RESET = "\033[0m"


class SyncService:
    """
    Service for syncing remediation progress.

    Separate from FinalizeService because:
    - Sync is repeatable (run after each fix)
    - Sync records real timestamps
    - Finalize is one-time (persist everything to DB)
    """

    def __init__(
        self,
        db_path: str | Path = "output/audit_history.db",
    ):
        """
        Initialize sync service.

        Args:
            db_path: Path to SQLite audit database
        """
        self.db_path = Path(db_path)
        self.store = HistoryStore(self.db_path)
        # Ensure schema exists (including action_log)
        self.store.initialize_schema()
        logger.info("SyncService initialized")

    def get_initial_run_id(self) -> int | None:
        """Get the first (baseline) audit run ID."""
        return self.store.get_initial_baseline_id()

    def get_latest_run_id(self) -> int | None:
        """Get the most recent audit run ID."""
        return self.store.get_latest_run_id()

    def sync(
        self,
        audit_service: "AuditService" = None,
        targets_file: str = "sql_targets.json",
        audit_manager: Any = None,
        audit_id: int | None = None,
    ) -> dict:
        """
        Sync remediation progress.

        1. Re-audit current state (creates new audit_run with type='sync')
        2. Diff against initial baseline
        3. Update action_log with real timestamps
        4. Inject actions into the Excel report and save it

        Args:
            audit_service: AuditService instance (creates new if None)
            targets_file: Targets config for re-audit
            audit_manager: Optional AuditManager for path resolution
            audit_id: Optional Audit ID context
        """
        # Get initial baseline
        initial_run_id = self.get_initial_run_id()
        if initial_run_id is None:
            logger.error("No baseline audit found. Run --audit first.")
            return {"error": "No baseline audit found"}

        # ---------------------------------------------------------------------
        # Pre-flight Check: Finalized State
        # ---------------------------------------------------------------------
        run = self.store.get_audit_run(initial_run_id)
        if run and run.status == "finalized":
            msg = f"Audit Run #{initial_run_id} is FINALIZED. Sync is blocked to preserve state."
            logger.error(msg)
            print(f"\n{RED}⛔ ERROR: {msg}{RESET}")
            print(f"To modify this audit, you must start a NEW baseline run.{RESET}\n")
            return {"error": "Audit is finalized"}

        # ---------------------------------------------------------------------
        # Pre-flight Check: File Locking
        # ---------------------------------------------------------------------
        # Ensure we can write to the output file before doing any work.
        path_latest = None
        if audit_manager and audit_id:
            path_latest = audit_manager.get_latest_excel_path(audit_id)
        else:
            path_latest = self.db_path.parent / "Audit_Latest.xlsx"

        if path_latest and path_latest.exists():
            try:
                with open(path_latest, "r+b"):
                    pass
            except IOError:
                logger.error("Output file is locked: %s", path_latest)
                return {
                    "error": f"FILE EXTANT & LOCKED: Close '{path_latest.name}' and try again."
                }

        logger.info("Sync: initial baseline run ID = %d", initial_run_id)

        # Initialize Writer explicitly with Metadata from Baseline
        # Note: 'run' variable already holds the baseline audit run info
        baseline_started_at = datetime.now()
        baseline_org = "Unspecified"

        if run:
            baseline_started_at = run.started_at or datetime.now()
            baseline_org = run.organization or "Unspecified"

        # Capture Pre-Scan State (Before re-audit overwrites instances)
        pre_scan_instances: dict[int, dict] = {}
        try:
            instances = self.store.get_all_instances()
            for i in instances:
                pre_scan_instances[i.id] = {
                    "v": i.version,
                    "l": i.product_level,
                    "e": i.edition,
                }
        except Exception as e:
            logger.warning("Could not capture pre-scan instances: %s", e)

        writer = EnhancedReportWriter()
        writer.set_audit_info(
            run_id=initial_run_id,  # Use baseline ID for the report ID
            organization=baseline_org,
            audit_name="Remediation Sync Report",
            started_at=baseline_started_at,
        )

        # ---------------------------------------------------------------------
        # PHASE 1: Annotation Sync (Read-Back)
        # ---------------------------------------------------------------------
        # Read user annotations from the EXISTING Excel report (if any)
        # This allows us to capture "Justification" from the user
        from autodbaudit.application.annotation_sync import AnnotationSyncService

        annot_sync = AnnotationSyncService(self.db_path)

        # If audit_manager/audit_id avail, use that path, else default
        excel_path = path_latest  # Already resolved in file locking check

        exception_count = 0

        if excel_path and excel_path.exists():
            logger.info("Sync: Reading annotations from %s", excel_path)

            # 1. Load existing DB state (for comparison)
            old_annotations = annot_sync.load_from_db()

            # 2. Read new specific annotations from Excel
            current_annotations = annot_sync.read_all_from_excel(excel_path)

            # 3. Persist to DB (Source of Truth)
            annot_sync.persist_to_db(current_annotations)

            # 4. Detect NEW Exceptions/Justifications
            # This logs distinct actions for newly addressed items
            exceptions = annot_sync.detect_exception_changes(
                old_annotations, current_annotations
            )

            now_iso = datetime.now(timezone.utc).isoformat()

            for ex in exceptions:
                # Log "Exception" action
                # entity_key from exceptions is just the key part (not type|key)
                # But detect_exception_changes returns full_key, entity_type, entity_key
                # Action Log expects entity_key relative to Finding (usually just the key part in most lists)
                # or "hostname\instance..."?
                # Findings usually use "Server|Instance|..." format

                # Check entity_key usage in store.get_findings vs annotation keys
                # Annotations keys are usually derived from column parts.
                # Ideally they match.

                ek = ex["entity_key"]  # e.g. "SRV\INST|sa"
                desc = f"Exception Documented: {ex['justification']}"

                self.store.upsert_action(
                    initial_run_id=initial_run_id,
                    entity_key=ek,
                    action_type="Exception",
                    status="exception",
                    action_date=now_iso,
                    description=desc,
                    sync_run_id=None,  # Will be updated to current_run_id later? No, this is PRE-run.
                    # Or we can link to initial_run_id as base.
                )
                exception_count += 1
                logger.info("Sync: Logged exception for %s", ek)

            # Count TOTAL documented exceptions (active) in the current set
            # This logic mimics the user's "Exception Count" expectation
            # Any item with a justification is a documented exception.
            documented_exceptions_count = sum(
                1
                for v in current_annotations.values()
                if v.get("justification") or v.get("review_status") == "Exception"
            )

        else:
            logger.info(
                "Sync: No existing Excel report found to read annotations from."
            )
            documented_exceptions_count = 0

        # ---------------------------------------------------------------------
        # PHASE 2: Re-Audit (Refreshed Scan) & Action Sheet Population
        # ---------------------------------------------------------------------
        logger.info("Sync: Running re-audit...")
        if audit_service is None:
            audit_service = AuditService(
                config_dir=Path("config"), output_dir=Path("output")
            )

        # 1. Prepare Writer with Action Log Data
        # We must populate the "Actions" sheet from the DB because collectors don't do it.
        # Use simple 'writer' variable from earlier initialization

        # Fetch ALL actions associated with this baseline
        # (History of fixes, regressions, exceptions)
        all_actions = self.store.get_actions_for_run(initial_run_id)

        if all_actions:
            logger.info(
                "Sync: Populating Actions sheet with %d entries", len(all_actions)
            )
            # Sort by action_date desc or asc? Usually history is best newest first or oldest first.
            # Let's sort oldest first (chronological) as it's a log.
            all_actions.sort(key=lambda x: x["action_date"] or "")

            for action in all_actions:
                logger.info(
                    "Sync: Adding action row: %s - %s",
                    action["entity_key"],
                    action["action_type"],
                )
                # Map DB fields to add_action params
                # Action Log DB: entity_key, action_type, status, action_date, description
                # Actions Sheet: server, instance, category, finding, risk, change_desc, type, date, notes

                # Parse entity key to get server/instance/category/finding?
                # E.g. "SRV\INST|sa" or "SRV|Login|name"
                # This is tricky. We need to reconstruct readable info.

                ek = action["entity_key"]
                parts = ek.split("|")
                # Attempt heuristic parsing
                server_name = parts[0] if len(parts) > 0 else "Unknown"
                # If key has "SRV\INST", split it
                instance_name = ""
                if "\\" in server_name:
                    s_parts = server_name.split("\\", 1)
                    server_name = s_parts[0]
                    instance_name = s_parts[1]

                # Category/Finding finding guessing
                # If we have finding details in action description?
                # "Fixed: Issue resolved"
                # Let's use action_type as Category fallback or parse?
                category = "General"
                finding_text = ek  # customized below

                if len(parts) > 1:
                    # Maybe "Login|sa"?
                    category = parts[1] if len(parts) > 1 else "Unknown"
                    finding_text = parts[2] if len(parts) > 2 else ek

                # Risk Level
                # Status "fixed" -> Low Risk (Good)
                # Status "regression" -> High Risk (Bad)
                # Status "exception" -> Low Risk (Accepted)
                status_db = action["status"].lower()
                risk = "Medium"
                if status_db == "fixed":
                    risk = "Low"
                elif status_db == "regression":
                    risk = "High"
                elif status_db == "exception":
                    risk = "Low"
                elif status_db == "new":
                    risk = "High"

                # Date parsing
                adate = None
                if action["action_date"]:
                    try:
                        adate = datetime.fromisoformat(action["action_date"])
                    except:
                        pass

                writer.add_action(
                    server_name=server_name,
                    instance_name=instance_name,
                    category=category,
                    finding=finding_text,
                    risk_level=risk,
                    recommendation=action["description"],  # Change Description
                    status=(
                        "Closed" if status_db in ("fixed", "exception") else "Open"
                    ),  # Change Type
                    found_date=adate,
                    notes=f"ID: {action.get('id', '')}",  # Or other metadata
                )

        try:
            # Pass pre-populated writer to run_audit
            # It will append other sheets and save the file
            audit_result = audit_service.run_audit(
                targets_file=targets_file, writer=writer, skip_save=False
            )
        except Exception as e:
            logger.error("Re-audit failed: %s", e)
            return {"error": f"Re-audit failed: {e}"}

        # Get new run ID and mark as sync type
        current_run_id = self.get_latest_run_id()
        if not current_run_id:
            logger.error("Could not determine current run ID after re-audit")
            return {"error": "Re-audit did not produce a run ID"}

        drift_count = 0  # Initialize for stats tracking

        if current_run_id == initial_run_id:
            logger.error("Re-audit did not create new run path (IDs match)")
            # Usually run_audit always creates a run.

        # Mark as sync run
        if current_run_id != initial_run_id:
            self.store.mark_run_as_sync(current_run_id)

            # -------------------------------------------------------------------------
            # Detect Version / info Drift
            # -------------------------------------------------------------------------
            # Compare 'instances' (now updated) with pre_scan_instances

            current_instances = self.store.get_all_instances()

            # Get existing actions context
            existing_actions_rows = self.store.get_actions_for_run(initial_run_id)
            existing_actions = {}
            for r in existing_actions_rows:
                existing_actions[r["entity_key"]] = {
                    "action_type": r["action_type"],
                    "action_date": r["action_date"],
                }

            drift_count = 0
            now_iso = datetime.now(timezone.utc).isoformat()

            for i in current_instances:
                iid = i.id
                if iid in pre_scan_instances:
                    old = pre_scan_instances[iid]
                    changes = []
                    # Check for None values to avoid comparison errors with strings?
                    # Store handles optional/None correctly usually.

                    new_v = i.version or ""
                    old_v = old["v"] or ""
                    if new_v != old_v:
                        changes.append(f"Version: {old_v} -> {new_v}")

                    new_l = i.product_level or ""
                    old_l = old["l"] or ""
                    if new_l != old_l:
                        changes.append(f"Level: {old_l} -> {new_l}")

                    new_e = i.edition or ""
                    old_e = old["e"] or ""
                    if new_e != old_e:
                        changes.append(f"Edition: {old_e} -> {new_e}")

                    if changes:
                        # Fetch names for key
                        server = self.store.get_server(i.server_id)

                        if server:
                            hostname = server.hostname
                            inst_name = i.instance_name
                            entity_key = (
                                f"{hostname}\\{inst_name}" if inst_name else hostname
                            )
                            key_suffix = "|System|Version"
                            full_key = f"{entity_key}{key_suffix}"

                            desc = f"System Update Detected: {', '.join(changes)}"
                            logger.info("Sync: %s", desc)

                            self.store.upsert_action(
                                initial_run_id=initial_run_id,
                                entity_key=full_key,
                                action_type="System Information",
                                status="fixed",
                                action_date=now_iso,
                                description=desc,
                                sync_run_id=current_run_id,
                            )
                            drift_count += 1

            # -------------------------------------------------------------------------
            # Calculate Findings Diffs (Baseline & Recent)
            # -------------------------------------------------------------------------
            baseline_findings = self.store.get_findings(initial_run_id)
            current_findings = self.store.get_findings(current_run_id)

            # Helper to calc diffs
            def calc_diff(old_list, new_list):
                old_map = {f["entity_key"]: f.get("status", "FAIL") for f in old_list}
                new_map = {f["entity_key"]: f.get("status", "FAIL") for f in new_list}

                fixed = 0
                regressed = 0
                still_failing = 0
                new_issues = 0

                # Check Old against New
                for key, old_status in old_map.items():
                    if key not in new_map:
                        if old_status in ("FAIL", "WARN"):
                            fixed += 1
                    else:
                        new_status = new_map[key]
                        if old_status in ("FAIL", "WARN") and new_status in (
                            "FAIL",
                            "WARN",
                        ):
                            still_failing += 1
                        elif old_status == "PASS" and new_status in ("FAIL", "WARN"):
                            regressed += 1

                # Check New against Old
                for key, new_status in new_map.items():
                    if key not in old_map and new_status in ("FAIL", "WARN"):
                        new_issues += 1

                return {
                    "fixed": fixed,
                    "still_failing": still_failing,
                    "regression": regressed,
                    "new": new_issues,
                }

            # 1. Baseline Diff
            baseline_stats = calc_diff(baseline_findings, current_findings)

            # 2. Recent Diff (Since last sync)
            prev_run_id = self.store.get_previous_sync_run(current_run_id)
            if prev_run_id:
                prev_findings = self.store.get_findings(prev_run_id)
                recent_stats = calc_diff(prev_findings, current_findings)
            else:
                recent_stats = baseline_stats.copy()  # First sync = baseline diff

            # Log Actions for Baseline Diff (as before) - we track progress against Baseline mostly?
            # Or against previous?
            # The Action Log is chronological. We effectively logged changes via annot_sync for "Exception".
            # For "Fixed" and "Regressed", we should log based on transition from *Previous* state to Current state.
            # If we fixed it compared to Baseline, but it was already fixed in previous Run, we don't want to duplicate the "Fixed" log entry.
            # So actual Action Logging should be comparing Prev -> Current.

            # Re-implement Action Logging using Prev->Current logic if available, else Baseline->Current
            ref_findings = (
                self.store.get_findings(prev_run_id)
                if prev_run_id
                else baseline_findings
            )
            ref_run_id = prev_run_id if prev_run_id else initial_run_id

            ref_map = {f["entity_key"]: f for f in ref_findings}
            cur_map = {f["entity_key"]: f for f in current_findings}

            for key, cur_f in cur_map.items():
                cur_status = cur_f.get("status", "FAIL")
                if key in ref_map:
                    ref_status = ref_map[key].get("status", "FAIL")
                    if ref_status == "PASS" and cur_status in ("FAIL", "WARN"):
                        # REGRESSION (Newly broken since last check)
                        self.store.upsert_action(
                            initial_run_id=initial_run_id,
                            entity_key=key,
                            action_type="Regression",
                            status="regression",
                            action_date=now_iso,
                            description=f"Regression: {cur_f.get('reason', 'Issue re-appeared')}",
                            sync_run_id=current_run_id,
                        )
                elif cur_status in ("FAIL", "WARN"):
                    # NEW (Since last check)
                    self.store.upsert_action(
                        initial_run_id=initial_run_id,
                        entity_key=key,
                        action_type="New",
                        status="new",
                        action_date=now_iso,
                        description=f"New Issue: {cur_f.get('reason', 'New issue detected')}",
                        sync_run_id=current_run_id,
                    )

            for key, ref_f in ref_map.items():
                if key not in cur_map:  # Gone -> Fixed?
                    ref_status = ref_f.get("status", "FAIL")
                    if ref_status in ("FAIL", "WARN"):
                        # FIXED (Since last check)
                        self.store.upsert_action(
                            initial_run_id=initial_run_id,
                            entity_key=key,
                            action_type="Fixed",
                            status="fixed",
                            action_date=now_iso,
                            description=f"Fixed: {ref_f.get('reason', 'Issue resolved')}",
                            sync_run_id=current_run_id,
                        )

            # -------------------------------------------------------------------------
            # PHASE 3: Write Back Annotations & Stats
            # -------------------------------------------------------------------------
            # Better to read fresh or use what we parsed.
            # Let's use the annotations we persisted.

            # NOTE: audit_service.run_audit overwrote the file.
            latest_annotations = annot_sync.load_from_db()
            annot_sync.write_all_to_excel(excel_path, latest_annotations)

            logger.info("Sync Complete. Run ID: %d", current_run_id)
        else:
            logger.warning("Sync run ID is same as initial? This might be a bug.")
            baseline_stats = {"fixed": 0, "still_failing": 0, "regression": 0, "new": 0}
            recent_stats = {"fixed": 0, "still_failing": 0, "regression": 0, "new": 0}
            exception_count = 0
            documented_exceptions_count = 0

        # Return dict matching CLI expectations
        return {
            "status": "success",
            "initial_run_id": initial_run_id,
            "current_run_id": current_run_id,
            "drift_count": drift_count,
            "exceptions": exception_count,  # New/Changed in this run
            "total_exceptions": documented_exceptions_count,  # Total active
            "baseline": baseline_stats,
            "recent": recent_stats,
        }
