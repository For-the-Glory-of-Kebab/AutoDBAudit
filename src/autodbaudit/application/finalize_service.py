"""
Finalize service - concludes the audit lifecycle.
"""

from __future__ import annotations

import hashlib
import logging
import shutil
from datetime import datetime
from pathlib import Path

from autodbaudit.infrastructure.sqlite import HistoryStore
from autodbaudit.application.exception_service import ExceptionService

logger = logging.getLogger(__name__)


class FinalizeService:
    """
    Service for finalizing audit runs.

    Enforces the end of the audit lifecycle:
    1. Verify current state (must not be already finalized)
    2. "Force" check (allow concluding even if findings remain Open?)
       - Actually, 'finalize' just means "we are done auditing".
       - It doesn't strictly require 0 findings, that's a policy decision.
       - The tool just locks the state.
    3. Update DB status to 'finalized'
    4. Archive/Lock the Excel report
    """

    def __init__(self, output_dir: Path | str = "output"):
        self.output_dir = Path(output_dir)
        self.db_path = self.output_dir / "audit_history.db"
        self.store = HistoryStore(self.db_path)

    def _find_latest_excel(self, excel_path: Path | str | None = None) -> Path | None:
        """
        Find the latest Excel report file.

        Search order:
        1. Use explicit path if provided and exists
        2. Look for Audit_Latest.xlsx in output_dir
        3. Search subdirectories for *_Latest.xlsx
        4. Search subdirectories for *.xlsx (get most recent by mtime)
        """
        if excel_path:
            path = Path(excel_path)
            if path.exists():
                return path

        # Direct path
        direct = self.output_dir / "Audit_Latest.xlsx"
        if direct.exists():
            return direct

        # Search in subdirectories for Audit_*_Latest.xlsx
        latest_pattern = list(self.output_dir.glob("**/Audit_*_Latest.xlsx"))
        if latest_pattern:
            latest_pattern.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return latest_pattern[0]

        # Fallback: any *_Latest.xlsx
        any_latest = list(self.output_dir.glob("**/*_Latest.xlsx"))
        if any_latest:
            any_latest.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return any_latest[0]

        # Last resort: most recent xlsx (excluding final/)
        any_xlsx = [
            p for p in self.output_dir.glob("**/*.xlsx") if "final" not in str(p)
        ]
        if any_xlsx:
            any_xlsx.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            return any_xlsx[0]

        return None

    def finalize(
        self,
        run_id: int | None = None,
        force: bool = False,
        excel_path: Path | str | None = None,
    ) -> dict:
        """
        Finalize an audit run.

        Orchestrates:
        1. Import latest annotations (Notes/Reasons) from Excel to DB
        2. Snapshot final configuration (reproducibility)
        3. Archive & Lock the report
        4. Mark DB status as localized
        """
        # 1. Resolve Run ID
        if run_id is None:
            run_id = self.store.get_latest_run_id()
            if not run_id:
                return {"error": "No audit runs found to finalize."}

        # 2. Check current status
        run = self.store.get_audit_run(run_id)
        if not run:
            return {"error": f"Run ID {run_id} not found."}

        if run.status == "finalized":
            return {
                "status": "already_finalized",
                "message": f"Run {run_id} is already finalized.",
            }

        # 2a. Enforce Strictness (unless force=True)
        if not force:
            status = self.get_finalization_status(run_id)
            if not status["can_finalize"]:
                return {
                    "error": f"Strict Finalization Block: {status.get('error')}. Use --force to override."
                }

        # 2b. Check if Excel file is locked (open in Excel)
        src_path = self._find_latest_excel(excel_path)
        if not src_path:
            src_path = self.output_dir / "Audit_Latest.xlsx"  # Fallback
        if src_path.exists():
            try:
                with open(src_path, "r+b"):
                    pass  # File is not locked
            except PermissionError:
                return {
                    "error": f"Excel file is open: {src_path.name}. Please close it and retry."
                }

        # 3. Import Annotations (Sync Excel -> DB)
        # This ensures the DB (Source of Truth) has the final human inputs
        logger.info("Finalize: Importing annotations from Excel to DB...")
        exc_service = ExceptionService(self.db_path, excel_path)
        exc_result = exc_service.apply_exceptions(run_id)

        if "error" in exc_result:
            # If we can't read the Excel (e.g. file open), we should probably block finalization
            # unless force is used?
            if not force:
                return {
                    "error": f"Annotation sync failed: {exc_result['error']}. Close file and retry."
                }
            logger.warning(
                "Forcing finalization despite annotation sync failure: %s",
                exc_result["error"],
            )

        # 4. Snapshot Configuration (Reproducibility)
        # We assume the current config on disk is what we want to lock as the "Final" state
        # (skipped for complexity/time constraints per previous decision)

        # 5. Archive Report - use discovered path
        src_path = self._find_latest_excel(excel_path)
        if not src_path or not src_path.exists():
            return {
                "error": f"Output report not found. Cannot finalize missing report."
            }

        final_dir = self.output_dir / "final"
        final_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        org_slug = (run.organization or "Org").replace(" ", "_")
        final_filename = f"{org_slug}_Audit_FINAL_{timestamp}_Run{run_id}.xlsx"
        final_path = final_dir / final_filename

        try:
            shutil.copy2(src_path, final_path)
            # Make read-only (platform compatible attempt)
            try:
                final_path.chmod(0o444)
            except Exception:
                pass
        except IOError as e:
            return {"error": f"Failed to archive report: {e}"}

        try:
            # 6. Compute Hash
            file_hash = self._compute_file_hash(final_path)

            # 7. Update DB
            self.store.complete_audit_run(run_id, "finalized")

            logger.info("Finalized Run %s. Hash: %s", run_id, file_hash)

            return {
                "status": "success",
                "run_id": run_id,
                "final_path": str(final_path),
                "hash": file_hash,
                "annotations_applied": exc_result.get("applied", 0),
                "forced": force,
            }
        except Exception as e:
            logger.exception("Finalization failed mid-process")
            # If we copied the file but DB update failed, we should probably delete the file
            # to prevent a "ghost" final report from existing.
            if final_path and final_path.exists():
                try:
                    final_path.unlink()
                except OSError:
                    pass  # Best effort cleanup
            return {"error": f"Critical Finalize Error: {e}"}

    def get_finalization_status(self, run_id: int | None = None) -> dict:
        """
        Check if a run is ready to be finalized.

        Returns:
            Dict with status info (can_finalize, outstanding counts, etc.)
        """
        if run_id is None:
            run_id = self.store.get_latest_run_id()
            if not run_id:
                return {"error": "No audit runs found."}

        # Check status
        run = self.store.get_audit_run(run_id)
        if not run:
            return {"error": f"Run {run_id} not found"}

        if run.status == "finalized":
            return {
                "can_finalize": False,
                "error": f"Run {run_id} is already finalized.",
            }

        # Check for outstanding findings
        findings = self.store.get_findings(run_id)

        fails = []
        warns = []

        for f in findings:
            if f["status"] == "FAIL":
                fails.append({"type": f["finding_type"], "entity": f["entity_key"]})
            elif f["status"] == "WARN":
                warns.append({"type": f["finding_type"], "entity": f["entity_key"]})

        # Strictness: allow finalize only if ZERO fails.
        # User must either remediate or Except (which changes status to PASS/EXCEPTED)
        can_finalize = len(fails) == 0

        # Construct result
        status = {
            "baseline_run_id": run_id,
            "can_finalize": can_finalize,
            "outstanding_fails": len(fails),
            "outstanding_warns": len(warns),
            "fail_details": fails[:10],  # Limit output
            "warn_details": warns[:10],
        }

        if not can_finalize:
            status["error"] = (
                f"Cannot finalize: {len(fails)} outstanding FAILs. Remediate or Except them first."
            )

        return status

    def _compute_file_hash(self, path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
