"""
RealDBTestContext - Main test context for real SQL Server testing.

Provides:
- CLI command execution
- Excel file access
- SQL fixture application
- Baseline tracking
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from tests.shared.helpers import CLIRunner, ExcelIO

if TYPE_CHECKING:
    from .baseline_manager import BaselineManager


class RealDBTestContext:
    """
    Context for tests against real SQL Server instances.

    Differences from mock TestContext:
    - Connects to real SQL instances (via config)
    - Runs actual CLI commands
    - Uses real Excel files
    - Tracks expected discrepancies
    """

    def __init__(
        self,
        project_root: Path,
        config_dir: Path,
        output_dir: Path,
        baseline_manager: BaselineManager,
    ) -> None:
        self.project_root = project_root
        self.config_dir = config_dir
        self.output_dir = output_dir
        self.baseline_manager = baseline_manager

        self.cli = CLIRunner(project_root)
        self.audit_id: int | None = None
        self.excel_path: Path | None = None
        self._excel_io: ExcelIO | None = None

        # Track what fixtures we've applied
        self.applied_fixtures: list[str] = []

    @property
    def excel(self) -> ExcelIO | None:
        """Get Excel I/O helper for current report."""
        if self.excel_path and self.excel_path.exists():
            if self._excel_io is None:
                self._excel_io = ExcelIO(self.excel_path)
            return self._excel_io
        return None

    @property
    def db_path(self) -> Path:
        """Path to audit_history.db."""
        return self.project_root / "data" / "audit_history.db"

    def get_db_connection(self) -> sqlite3.Connection:
        """Get connection to audit history database."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # ═══════════════════════════════════════════════════════════════════════
    # CLI OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def run_audit(self) -> int | None:
        """
        Run audit command.

        Returns:
            Audit ID if successful, None otherwise
        """
        result = self.cli.audit()

        if result.success and result.audit_id:
            self.audit_id = result.audit_id
            self._find_excel()
            return self.audit_id

        return None

    def run_sync(self) -> dict:
        """
        Run sync command.

        Returns:
            Stats dict from sync output
        """
        if not self.audit_id:
            raise RuntimeError("No audit ID - run audit first")

        # Close Excel if open (prevent lock)
        if self._excel_io:
            self._excel_io.close()
            self._excel_io = None

        result = self.cli.sync(self.audit_id)
        return result.stats

    def run_finalize(self, persian: bool = False) -> bool:
        """Run finalize command."""
        if not self.audit_id:
            raise RuntimeError("No audit ID")

        result = self.cli.finalize(self.audit_id, persian=persian)
        return result.success

    def run_definalize(self) -> bool:
        """Run definalize command."""
        if not self.audit_id:
            raise RuntimeError("No audit ID")

        result = self.cli.definalize(self.audit_id)
        return result.success

    def _find_excel(self) -> None:
        """Find the Excel file created by audit."""
        output_dir = self.project_root / "output"

        # Search recursively - Excel may be in audit subdirectory
        # e.g., output/audit_001/Audit_001_Latest.xlsx
        excels = list(output_dir.glob("**/*.xlsx"))

        # Exclude Persian translations
        excels = [e for e in excels if "_fa" not in e.stem]

        if excels:
            # Get most recent
            self.excel_path = max(excels, key=lambda p: p.stat().st_mtime)

    # ═══════════════════════════════════════════════════════════════════════
    # EXCEL OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def write_annotation(
        self,
        sheet: str,
        row: int,
        notes: str | None = None,
        justification: str | None = None,
        review_status: str | None = None,
    ) -> bool:
        """Write annotation to Excel row."""
        if not self.excel:
            return False

        result = self.excel.write_annotation(
            sheet, row, notes, justification, review_status
        )
        self.excel.save()
        return result

    # ═══════════════════════════════════════════════════════════════════════
    # FIXTURE OPERATIONS
    # ═══════════════════════════════════════════════════════════════════════

    def apply_fixture(self, fixture_name: str) -> bool:
        """
        Apply a SQL fixture.

        Args:
            fixture_name: Name of fixture (e.g., "sa_enable")

        Returns:
            True if applied successfully
        """
        from .sql_executor import SQLExecutor

        fixture_path = (
            Path(__file__).parent.parent / "fixtures" / "atomic" / f"{fixture_name}.sql"
        )

        if not fixture_path.exists():
            return False

        executor = SQLExecutor(self.config_dir)
        success = executor.execute_file(fixture_path)

        if success:
            self.applied_fixtures.append(fixture_name)
            self.baseline_manager.record_addition(fixture_name)

        return success

    def revert_fixtures(self) -> None:
        """Revert all applied fixtures."""
        from .sql_executor import SQLExecutor

        executor = SQLExecutor(self.config_dir)

        for fixture in self.applied_fixtures:
            revert_name = fixture.replace("_enable", "_disable").replace(
                "_create", "_drop"
            )
            revert_path = (
                Path(__file__).parent.parent
                / "fixtures"
                / "atomic"
                / f"{revert_name}.sql"
            )
            if revert_path.exists():
                executor.execute_file(revert_path)

        self.applied_fixtures.clear()

    # ═══════════════════════════════════════════════════════════════════════
    # CLEANUP
    # ═══════════════════════════════════════════════════════════════════════

    def cleanup(self) -> None:
        """Clean up test resources."""
        if self._excel_io:
            self._excel_io.close()
            self._excel_io = None

        # Don't revert fixtures by default - let test control this
