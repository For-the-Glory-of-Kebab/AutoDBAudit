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
        targets_file: str | None = "sql_targets.json",
        audit_manager: Any = None,
        audit_id: int | None = None,
    ) -> dict:
        """
        Sync remediation progress.

        1. Re-audit current state (creates new audit_run with type='sync')
        2. Diff against PRIOR SUCCESSFUL SYNC + BASELINE
        3. Update action_log with real timestamps
        4. Inject actions into the Excel report and save it to 'output/sync_runs/'

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

        targets_file = targets_file or "sql_targets.json"
        
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
        # Paths & Locking
        # ---------------------------------------------------------------------
        # Output Logic: cleaner structure
        # Output Logic: cleaner structure
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # sync_folder = self.db_path.parent / "sync_runs"
        # sync_folder.mkdir(exist_ok=True)
        # Note: User requested not to use subfolders / nested structures
        output_dir = self.db_path.parent
        
        # We save to a new timestamped file in root output
        final_excel_path = output_dir / f"sync_report_{timestamp}.xlsx"
        
        # We also need to READ from the "Latest" user file to get annotations
        # Default to "Audit_Latest.xlsx" in output root unless managed
        if audit_manager and audit_id:
            input_excel_path = audit_manager.get_latest_excel_path(audit_id)
        else:
            input_excel_path = self.db_path.parent / "Audit_Latest.xlsx"

        logger.info("Sync: initial baseline run ID = %d", initial_run_id)

        # Initialize Writer Data
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
            run_id=initial_run_id,
            organization=baseline_org,
            audit_name="Remediation Sync Report",
            started_at=baseline_started_at,
        )

        # ---------------------------------------------------------------------
        # PHASE 1: Annotation Sync (Read-Back)
        # ---------------------------------------------------------------------
        from autodbaudit.application.annotation_sync import AnnotationSyncService

        annot_sync = AnnotationSyncService(self.db_path)
        exception_count = 0
        documented_exceptions_count = 0
        deferred_exception_actions = []

        if input_excel_path and input_excel_path.exists():
            logger.info("Sync: Reading annotations from %s", input_excel_path)
            old_annotations = annot_sync.load_from_db()
            current_annotations = annot_sync.read_all_from_excel(input_excel_path)
            annot_sync.persist_to_db(current_annotations)

            # Detect NEW Exceptions/Justifications
            exceptions = annot_sync.detect_exception_changes(
                old_annotations, current_annotations
            )

            now_iso = datetime.now(timezone.utc).isoformat()

            for ex in exceptions:
                # Store Action Data for later committing
                desc = f"Exception Documented: {ex['justification']}"
                deferred_exception_actions.append({
                    "initial_run_id": initial_run_id,
                    "entity_key": ex["full_key"],
                    "action_type": "Exception",
                    "status": "exception",
                    "action_date": now_iso,
                    "description": desc,
                })
                exception_count += 1
                logger.info("Sync: Found exception for %s", ex["full_key"])

            documented_exceptions_count = sum(
                1
                for v in current_annotations.values()
                if v.get("justification") or v.get("review_status") == "Exception" or v.get("notes")
            )
        else:
            logger.info("Sync: No existing Excel report found to read annotations from.")

        # ---------------------------------------------------------------------
        # PHASE 2: Re-Audit (Refreshed Scan) & Action Sheet Population
        # ---------------------------------------------------------------------
        logger.info("Sync: Running re-audit...")
        if audit_service is None:
            audit_service = AuditService(
                config_dir=Path("config"), output_dir=Path("output")
            )

        # 1. Prepare Writer with Action Log Data
        all_actions = self.store.get_actions_for_run(initial_run_id)
        
        # Inject Deferred Exceptions (so they appear in THIS report)
        for ex in deferred_exception_actions:
            # ex has keys: initial_run_id, entity_key, action_type, status, action_date, description
            # Matches DB row dict structure enough for our loop
            all_actions.append(ex)

        if all_actions:
            logger.info("Sync: Populating Actions sheet with %d entries", len(all_actions))
            # Sort by date, treating None as empty string
            all_actions.sort(key=lambda x: x.get("action_date") or "")

            for action in all_actions:
                ek = action["entity_key"]
                parts = ek.split("|")
                # Heuristic parsing for display
                # Format usually: TYPE|Server|Instance|FindingKey...
                # Or just Server|Instance|... 
                
                # Try to extract readable parts
                server_name = "Unknown"
                instance_name = ""
                category = action["action_type"]
                finding_text = ek
                
                if len(parts) >= 3:
                     # Check if first part looks like type
                     if parts[0] in ["sa_account", "backup", "service", "config", "login"]:
                         server_name = parts[1]
                         instance_name = parts[2]
                         category = parts[0].title()
                         finding_text = "|".join(parts[3:]) if len(parts) > 3 else ek
                     else:
                         # Assume Server|Instance|...
                         server_name = parts[0]
                         instance_name = parts[1]
                         finding_text = "|".join(parts[2:]) if len(parts) > 2 else ek

                status_db = action["status"].lower()
                risk = "Low" if status_db in ("fixed", "exception") else "High"

                adate = None
                if action.get("action_date"):
                    try:
                        adate = datetime.fromisoformat(action["action_date"])
                    except Exception:
                        pass

                writer.add_action(
                    server_name=server_name,
                    instance_name=instance_name,
                    category=category,
                    finding=finding_text,
                    risk_level=risk,
                    recommendation=action.get("description", ""),
                    status=("Closed" if status_db in ("fixed", "exception") else "Open"),
                    found_date=adate,
                    notes=f"ID:{action.get('id', 'new')}",
                )

        try:
            # SKIP SAVE internally so we can control path
            processed_writer = audit_service.run_audit(
                targets_file=targets_file, writer=writer, skip_save=True
            )
        except Exception as e:
            logger.error("Re-audit failed: %s", e)
            return {"error": f"Re-audit failed: {e}"}

        # Get new run ID
        current_run_id = self.get_latest_run_id()
        if not current_run_id:
            return {"error": "Re-audit did not produce a run ID"}

        if current_run_id != initial_run_id:
            self.store.mark_run_as_sync(current_run_id)

            # -------------------------------------------------------------------------
            # 0. Commit Deferred Actions (Exceptions detected in Phase 1)
            # -------------------------------------------------------------------------
            for ex_action_data in deferred_exception_actions:
                self.store.upsert_action(
                    initial_run_id=ex_action_data["initial_run_id"],
                    entity_key=ex_action_data["entity_key"],
                    action_type=ex_action_data["action_type"],
                    status=ex_action_data["status"],
                    action_date=ex_action_data["action_date"],
                    description=ex_action_data["description"],
                    sync_run_id=current_run_id,
                )
                logger.info("Sync: Logged exception for %s with sync_run_id %d", ex_action_data["entity_key"], current_run_id)

            # -------------------------------------------------------------------------
            # 1. Detect Version / System Info Drift
            # -------------------------------------------------------------------------
            current_instances = self.store.get_all_instances()
            drift_count = 0
            
            for i in current_instances:
                iid = i.id
                if iid in pre_scan_instances:
                    old = pre_scan_instances[iid]
                    changes = []

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
                        server = self.store.get_server(i.server_id)
                        if server:
                            hostname = server.hostname
                            inst_name = i.instance_name
                            entity_key = f"{hostname}\\{inst_name}" if inst_name else hostname
                            full_key = f"{entity_key}|System|Version"

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
            # 2. Calculate Findings Diffs
            # -------------------------------------------------------------------------
            baseline_findings = self.store.get_findings(initial_run_id)
            current_findings = self.store.get_findings(current_run_id)
            
            # --- Valid Instances Filter ---
            # To prevent false "Fixed" when connection fails:
            # Get list of instances that were SUCCESSFULLY scanned in CURRENT run
            valid_scanned_pairs = self.store.get_instances_for_run(current_run_id)
            # Create a set of "Server|Instance" strings for fast lookup
            valid_instance_keys = set()
            for s, i in valid_scanned_pairs:
                iname = i.instance_name if i.instance_name else "(Default)"
                # Key format varies, but usually starts with Hostname|Instance
                valid_instance_keys.add(f"{s.hostname}|{i.instance_name or ''}".lower())
                valid_instance_keys.add(f"{s.hostname}|{i.instance_name or '(Default)'}".lower())
            
            def is_valid_instance_key(key: str) -> bool:
                # Naive check: does the key start with any valid server|instance?
                # Keys are typically: "Type|Server|Instance|..." or "Server|Instance|..."
                # We normalize key to lower case
                key_lower = key.lower()
                for valid in valid_instance_keys:
                    # Robust check: split key by pipe and match first two
                    parts = key_lower.split("|")
                    
                    # Handle "Type|Server|Instance" format (Annotations style)
                    if len(parts) >= 3 and f"{parts[1]}|{parts[2]}" == valid:
                        return True
                    
                    # Handle "Server|Instance" format (Old findings style?)
                    if len(parts) >= 2 and f"{parts[0]}|{parts[1]}" == valid:
                        return True
                return False

            # --- Reference Run ---
            # Use Last SUCCESSFUL Sync Run as baseline for "New/Fixed" relative changes
            prev_run_id = self.store.get_previous_sync_run(current_run_id)
            
            ref_findings = (
                self.store.get_findings(prev_run_id)
                if prev_run_id
                else baseline_findings
            )
            
            ref_map = {f["entity_key"]: f for f in ref_findings}
            cur_map = {f["entity_key"]: f for f in current_findings}
            
            now_iso = datetime.now(timezone.utc).isoformat()
            
            # 1. Detect New Issues / Regressions (Cur vs Ref)
            for key, cur_f in cur_map.items():
                cur_status = cur_f.get("status", "FAIL")
                
                # Only check if valid instance (sanity check, though findings imply valid scan)
                # But mostly we care about Ref vs Cur
                
                if key in ref_map:
                    ref_status = ref_map[key].get("status", "FAIL")
                    if ref_status == "PASS" and cur_status in ("FAIL", "WARN"):
                        # REGRESSION
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
                    # NEW Issue
                    self.store.upsert_action(
                        initial_run_id=initial_run_id,
                        entity_key=key,
                        action_type="New",
                        status="new",
                        action_date=now_iso,
                        description=f"New Issue: {cur_f.get('reason', 'New issue detected')}",
                        sync_run_id=current_run_id,
                    )

            # 2. Detect Fixes (Ref vs Cur)
            for key, ref_f in ref_map.items():
                if key not in cur_map:
                    # Candidate for "Fixed"
                    # CRITICAL: Check if instance was actually scanned
                    if not is_valid_instance_key(key):
                        logger.warning("Sync: Skipping 'Fixed' check for %s (Instance not scanned)", key)
                        continue
                    
                    ref_status = ref_f.get("status", "FAIL")
                    if ref_status in ("FAIL", "WARN"):
                        # FIXED
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
            # PHASE 3: Write Back Annotations & Save
            # -------------------------------------------------------------------------
            latest_annotations = annot_sync.load_from_db()
            
            if hasattr(processed_writer, 'save'):
                processed_writer.save(final_excel_path)
            else:
                logger.error("Processed writer does not support save")
            
            annot_sync.write_all_to_excel(final_excel_path, latest_annotations)
            
            logger.info("Sync Complete. Report saved to: %s", final_excel_path)
            
            # Update Audit_Latest.xlsx as well for convenience (UI)
            try:
                import shutil
                shutil.copy2(final_excel_path, self.db_path.parent / "Audit_Latest.xlsx")
                logger.info("Updated Audit_Latest.xlsx")
            except Exception as e:
                logger.warning("Could not update Audit_Latest.xlsx: %s", e)

            # -------------------------------------------------------------------------
            # Calculate Stats (Baseline & Recent)
            # -------------------------------------------------------------------------
            def calc_diff(old_list, new_list):
                old_map = {f["entity_key"]: f.get("status", "FAIL") for f in old_list}
                new_map = {f["entity_key"]: f.get("status", "FAIL") for f in new_list}

                fixed = 0
                regressed = 0
                still_failing = 0
                new_issues = 0

                # Check Old against New (Fixed vs Still Failing)
                for key, old_status in old_map.items():
                    if key not in new_map:
                        # Only count as fixed if it was a FAIL/WARN and instance was scanned
                        # (We assume implicit validity since we filtered findings? No, need check)
                        if old_status in ("FAIL", "WARN"):
                             if is_valid_instance_key(key):
                                 fixed += 1
                    else:
                        new_status = new_map[key]
                        if old_status in ("FAIL", "WARN") and new_status in ("FAIL", "WARN"):
                            still_failing += 1
                        elif old_status == "PASS" and new_status in ("FAIL", "WARN"):
                            regressed += 1

                # Check New against Old (New Issues)
                for key, new_status in new_map.items():
                    if key not in old_map and new_status in ("FAIL", "WARN"):
                        new_issues += 1

                return {
                    "fixed": fixed,
                    "still_failing": still_failing,
                    "regression": regressed,
                    "new": new_issues,
                }

            baseline_stats = calc_diff(baseline_findings, current_findings)

            if prev_run_id:
                prev_findings = self.store.get_findings(prev_run_id)
                recent_stats = calc_diff(prev_findings, current_findings)
            else:
                recent_stats = baseline_stats.copy()

        return {
            "status": "success",
            "initial_run_id": initial_run_id,
            "current_run_id": current_run_id,
            "drift_count": 0,
            "exceptions": exception_count,
            "total_exceptions": documented_exceptions_count,
            "baseline": baseline_stats,
            "recent": recent_stats,
            "report_path": str(final_excel_path),
        }
