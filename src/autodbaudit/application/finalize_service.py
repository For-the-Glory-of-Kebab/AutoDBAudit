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

        # 2b. Check if Excel file is locked (open in Excel)
        src_path = (
            Path(excel_path) if excel_path else (self.output_dir / "Audit_Latest.xlsx")
        )
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

        # 5. Archive Report
        src_path = (
            Path(excel_path) if excel_path else (self.output_dir / "Audit_Latest.xlsx")
        )
        if not src_path.exists():
            # Fallback to default
            src_path = self.output_dir / "Audit_Latest.xlsx"

        if not src_path.exists():
            return {
                "error": f"Output report not found at {src_path}. Cannot finalize missing report."
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

        # Check if they have exceptions?
        # (Naive check: count them. If user wants to finalize with fails, they use --force)

        can_finalize = len(fails) == 0

        return {
            "baseline_run_id": run_id,
            "can_finalize": can_finalize,
            "outstanding_fails": len(fails),
            "outstanding_warns": len(warns),
            "fail_details": fails[:10],  # Limit output
            "warn_details": warns[:10],
        }

    def _compute_file_hash(self, path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
