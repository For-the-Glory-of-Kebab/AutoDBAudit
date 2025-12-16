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

        # Run new audit (Capture Data Only)
        logger.info("Sync: Running re-audit...")
        if audit_service is None:
            audit_service = AuditService(
                config_dir=Path("config"), output_dir=Path("output")
            )

        try:
            # Pass writer and skip saving
            audit_service.run_audit(
                targets_file=targets_file, writer=writer, skip_save=True
            )
            # NOTE: run_audit will scan the updated (live) instances and update the DB
            # 'instances' table with the LATEST version info through HistoryStore logic.
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

            if drift_count > 0:
                logger.info("Sync: Detected %d system version changes.", drift_count)

            logger.info("Sync: current run ID = %d", current_run_id)
        else:
            logger.warning("Sync run ID is same as initial? This might be a bug.")

        return {
            "status": "success",
            "drift_count": drift_count,
            "run_id": current_run_id,
            "baseline_run_id": initial_run_id,
        }
