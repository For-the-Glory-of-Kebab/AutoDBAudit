"""
Annotation Sync Service - Main Orchestrator.

Provides the primary interface for bidirectional synchronization
of user annotations between Excel reports and SQLite database.

This is the only class external code should import from the sync package.
All other modules are internal implementation details.

Usage:
    from autodbaudit.application.sync import AnnotationSyncService

    sync = AnnotationSyncService("output/audit_history.db")

    # Read from Excel
    annotations = sync.read_all_from_excel("report.xlsx")

    # Persist to DB
    sync.persist_to_db(annotations)

    # Write back to Excel
    sync.write_all_to_excel("report.xlsx", annotations)
"""

from __future__ import annotations

import logging
from pathlib import Path

from autodbaudit.application.sync.config import get_all_sync_configs
from autodbaudit.application.sync.excel_reader import read_all_sheets
from autodbaudit.application.sync.excel_writer import write_all_sheets
from autodbaudit.application.sync.differ import (
    diff_annotations,
    DiffResult,
)

logger = logging.getLogger(__name__)


class AnnotationSyncService:
    """
    Bidirectional annotation sync between Excel and SQLite.

    This class orchestrates the modular sync components:
    - excel_reader: Read annotations from Excel
    - excel_writer: Write annotations to Excel
    - db_ops: Persist/load from SQLite
    - differ: Detect changes between states

    Implements AnnotationsProvider protocol for StatsService.
    """

    def __init__(self, db_path: str | Path = "output/audit_history.db") -> None:
        """Initialize with database path."""
        self.db_path = Path(db_path)
        self._sheet_configs = get_all_sync_configs()

    def read_all_from_excel(self, excel_path: Path | str) -> dict[str, dict]:
        """
        Read all annotations from configured sheets in Excel.

        Args:
            excel_path: Path to Excel file

        Returns:
            Dict of {entity_type|entity_key: {field_name: value}}
        """
        return read_all_sheets(excel_path, self._sheet_configs)

    def write_all_to_excel(
        self,
        excel_path: Path | str,
        annotations: dict[str, dict],
    ) -> int:
        """
        Write annotations back to Excel file.

        Args:
            excel_path: Path to Excel file
            annotations: Dict from read_all_from_excel

        Returns:
            Number of cells updated
        """
        return write_all_sheets(excel_path, annotations, self._sheet_configs)

    def persist_to_db(self, annotations: dict[str, dict]) -> int:
        """
        Persist all annotations to SQLite database.

        Args:
            annotations: Dict from read_all_from_excel

        Returns:
            Number of annotations saved
        """
        from autodbaudit.utils.database import persist_annotations_to_db
        return persist_annotations_to_db(self.db_path, annotations)

    def load_from_db(self) -> dict[str, dict]:
        """
        Load all annotations from SQLite database.

        Returns:
            Dict of {entity_type|entity_key: {field_name: value}}
        """
        from autodbaudit.utils.database import load_annotations_from_db
        return load_annotations_from_db(self.db_path)

    def get_all_annotations(self) -> dict[str, dict]:
        """
        Get all annotations keyed by entity_key.

        This is an alias for load_from_db() to satisfy the
        AnnotationsProvider protocol expected by StatsService.

        Returns:
            Dict of {entity_type|entity_key: {field_name: value}}
        """
        return self.load_from_db()

    def detect_exception_changes(
        self,
        old_annotations: dict[str, dict],
        new_annotations: dict[str, dict],
        current_findings: list[dict] | None = None,
    ) -> DiffResult:
        """
        Compare annotations to detect new/changed/removed exceptions.

        Args:
            old_annotations: Previous state
            new_annotations: Current state
            current_findings: Optional list of finding dicts

        Returns:
            DiffResult with change counts and affected keys
        """
        # Build set of discrepant keys if findings provided
        discrepant_keys = None
        if current_findings:
            discrepant_keys = set()
            for f in current_findings:
                status = str(f.get("status", "")).lower()
                if status in ("fail", "warn"):
                    key = f.get("entity_key", "")
                    if key:
                        discrepant_keys.add(key.lower())

        return diff_annotations(
            old_annotations,
            new_annotations,
            discrepant_keys,
        )
