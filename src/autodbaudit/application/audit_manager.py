"""
Audit Manager Module.

Manages the lifecycle of audits including folder creation,
metadata tracking, run numbering, and remediation versioning.

Each audit is a logical entity that can span multiple runs
(for credential fixes, adding servers, etc.) and produces
a final merged report via --finalize.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AuditManager:
    """
    Manages audit lifecycle and folder structure.

    Uses single global DB (audit_history.db) for all audits.
    Per-audit folders are for files only (Excel, scripts).

    Folder structure:
        output/
        ├── audit_history.db       # Single DB for ALL audits
        ├── audit_001/
        │   ├── audit.json         # Metadata (JSON)
        │   ├── Audit_001_Latest.xlsx
        │   ├── runs/run_001/, run_002/
        │   └── remediation/v001/, v002/
        └── audit_002/
    """

    def __init__(self, output_dir: str = "output"):
        """
        Initialize audit manager.

        Args:
            output_dir: Base output directory
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("AuditManager initialized with output dir: %s", self.output_dir)

    def create_new_audit(
        self,
        name: str = "",
        environment: str = "",
        notes: str = "",
    ) -> int:
        """
        Create a new audit with auto-incremented ID.

        Args:
            name: Human-readable audit name
            environment: Environment tag (production, test, etc.)
            notes: Additional notes

        Returns:
            The new audit ID
        """
        # Find next available ID
        existing_ids = self._get_existing_audit_ids()
        new_id = max(existing_ids, default=0) + 1

        # Create audit folder
        audit_folder = self._get_audit_folder(new_id)
        audit_folder.mkdir(parents=True, exist_ok=True)
        (audit_folder / "remediation").mkdir(exist_ok=True)

        # Generate default name if not provided
        if not name:
            name = f"Audit {new_id} - {datetime.now().strftime('%Y-%m-%d')}"

        # Create metadata
        metadata = {
            "id": new_id,
            "name": name,
            "environment": environment,
            "created": datetime.now().isoformat(),
            "status": "in_progress",
            "notes": notes,
            "runs": [],
            "remediation_versions": 0,
        }

        self._save_metadata(new_id, metadata)
        logger.info("Created new audit #%d: %s", new_id, name)

        return new_id

    def get_audit(self, audit_id: int) -> Optional[dict]:
        """
        Get audit metadata by ID.

        Args:
            audit_id: Audit ID

        Returns:
            Audit metadata dict or None if not found
        """
        metadata_path = self._get_audit_folder(audit_id) / "audit.json"
        if not metadata_path.exists():
            return None

        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def list_audits(self) -> list[dict]:
        """
        List all audits.

        Returns:
            List of audit metadata dicts, sorted by ID
        """
        audits = []
        for audit_id in sorted(self._get_existing_audit_ids()):
            metadata = self.get_audit(audit_id)
            if metadata:
                audits.append(metadata)
        return audits

    def get_latest_audit(self) -> Optional[dict]:
        """
        Get the most recent audit.

        Returns:
            Audit metadata dict or None if no audits exist
        """
        audit_ids = self._get_existing_audit_ids()
        if not audit_ids:
            return None
        return self.get_audit(max(audit_ids))

    def create_run(self, audit_id: int) -> int:
        """
        Create a new run within an audit.

        Args:
            audit_id: Audit ID

        Returns:
            The new run number
        """
        metadata = self.get_audit(audit_id)
        if not metadata:
            raise ValueError(f"Audit {audit_id} not found")

        # Find next run number
        run_num = len(metadata.get("runs", [])) + 1

        # NOTE: No run folder created - all data lives in SQLite
        # Excel working copy is in audit root folder

        # Update metadata
        run_info = {
            "run_id": run_num,
            "timestamp": datetime.now().isoformat(),
            "status": "running",
        }
        metadata.setdefault("runs", []).append(run_info)
        self._save_metadata(audit_id, metadata)

        logger.info("Created run #%d for audit #%d", run_num, audit_id)
        return run_num

    def complete_run(
        self,
        audit_id: int,
        run_num: int,
        servers: int = 0,
        findings: int = 0,
    ) -> None:
        """
        Mark a run as complete and update stats.

        Args:
            audit_id: Audit ID
            run_num: Run number
            servers: Number of servers audited
            findings: Number of findings
        """
        metadata = self.get_audit(audit_id)
        if not metadata:
            return

        for run in metadata.get("runs", []):
            if run.get("run_id") == run_num:
                run["status"] = "complete"
                run["completed"] = datetime.now().isoformat()
                run["servers"] = servers
                run["findings"] = findings
                break

        self._save_metadata(audit_id, metadata)

    def create_remediation_version(self, audit_id: int) -> int:
        """
        Create a new remediation script version.

        Args:
            audit_id: Audit ID

        Returns:
            The new version number
        """
        metadata = self.get_audit(audit_id)
        if not metadata:
            raise ValueError(f"Audit {audit_id} not found")

        version = metadata.get("remediation_versions", 0) + 1

        # Create version folder
        version_folder = self._get_remediation_folder(audit_id, version)
        version_folder.mkdir(parents=True, exist_ok=True)

        # Update metadata
        metadata["remediation_versions"] = version
        self._save_metadata(audit_id, metadata)

        logger.info("Created remediation v%d for audit #%d", version, audit_id)
        return version

    def set_audit_status(self, audit_id: int, status: str) -> None:
        """
        Update audit status.

        Args:
            audit_id: Audit ID
            status: New status (in_progress, finalized, etc.)
        """
        metadata = self.get_audit(audit_id)
        if metadata:
            metadata["status"] = status
            if status == "finalized":
                metadata["finalized_at"] = datetime.now().isoformat()
            self._save_metadata(audit_id, metadata)

    # ========== Path Helpers ==========

    def _get_audit_folder(self, audit_id: int) -> Path:
        """Get path to audit folder."""
        return self.output_dir / f"audit_{audit_id:03d}"

    def _get_run_folder(self, audit_id: int, run_num: int) -> Path:
        """Get path to run folder."""
        return self._get_audit_folder(audit_id) / "runs" / f"run_{run_num:03d}"

    def _get_remediation_folder(self, audit_id: int, version: int) -> Path:
        """Get path to remediation version folder."""
        return self._get_audit_folder(audit_id) / "remediation" / f"v{version:03d}"

    def get_global_db_path(self) -> Path:
        """Get path to global SQLite database (shared by all audits)."""
        return self.output_dir / "audit_history.db"

    def get_run_excel_path(self, audit_id: int, run_num: int) -> Path:
        """Get path to run's Excel snapshot (hidden temp file)."""
        temp_dir = self._get_audit_folder(audit_id) / ".temp_runs"
        temp_dir.mkdir(exist_ok=True)
        return temp_dir / f"run_{run_num:03d}_snapshot.xlsx"

    def get_latest_excel_path(self, audit_id: int) -> Path:
        """Get path to latest Excel report in audit root."""
        return self._get_audit_folder(audit_id) / f"Audit_{audit_id:03d}_Latest.xlsx"

    def get_final_excel_path(self, audit_id: int) -> Path:
        """Get path to finalized Excel report."""
        return self._get_audit_folder(audit_id) / f"FINAL_Audit_{audit_id:03d}.xlsx"

    def get_remediation_scripts_folder(self, audit_id: int, version: int) -> Path:
        """Get path to remediation scripts folder."""
        return self._get_remediation_folder(audit_id, version)

    def _get_existing_audit_ids(self) -> list[int]:
        """Get list of existing audit IDs."""
        ids = []
        for folder in self.output_dir.iterdir():
            if folder.is_dir() and folder.name.startswith("audit_"):
                try:
                    audit_id = int(folder.name.split("_")[1])
                    ids.append(audit_id)
                except (IndexError, ValueError):
                    pass
        return ids

    def _save_metadata(self, audit_id: int, metadata: dict) -> None:
        """Save audit metadata to JSON file."""
        metadata_path = self._get_audit_folder(audit_id) / "audit.json"
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def save_config_snapshot(
        self,
        audit_id: int,
        sql_targets: dict | list,
        audit_config: dict | None = None,
    ) -> None:
        """
        Save config snapshot for reproducibility.

        Args:
            audit_id: Audit ID
            sql_targets: sql_targets.json content
            audit_config: audit_config.json content (optional)
        """
        audit_folder = self._get_audit_folder(audit_id)

        # Save sql_targets snapshot
        targets_path = audit_folder / "sql_targets.snapshot.json"
        with open(targets_path, "w", encoding="utf-8") as f:
            json.dump(sql_targets, f, indent=2, ensure_ascii=False)
        logger.info("Saved sql_targets snapshot for audit #%d", audit_id)

        # Save audit_config snapshot if provided
        if audit_config:
            config_path = audit_folder / "audit_config.snapshot.json"
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(audit_config, f, indent=2, ensure_ascii=False)
            logger.info("Saved audit_config snapshot for audit #%d", audit_id)

    def get_config_snapshot(self, audit_id: int) -> dict:
        """
        Get config snapshot for an audit.

        Args:
            audit_id: Audit ID

        Returns:
            Dict with 'sql_targets' and optionally 'audit_config'
        """
        audit_folder = self._get_audit_folder(audit_id)
        result = {}

        targets_path = audit_folder / "sql_targets.snapshot.json"
        if targets_path.exists():
            with open(targets_path, "r", encoding="utf-8") as f:
                result["sql_targets"] = json.load(f)

        config_path = audit_folder / "audit_config.snapshot.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                result["audit_config"] = json.load(f)

        return result
