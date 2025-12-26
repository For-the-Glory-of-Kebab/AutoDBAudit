"""
Stats Assertions - CLI/Excel/DB count consistency verification.

Verifies statistics are accurate across all outputs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import sqlite3
    from openpyxl.workbook import Workbook


@dataclass
class AuditStats:
    """Audit statistics from any source."""

    total_findings: int = 0
    active_issues: int = 0
    exceptions: int = 0
    compliant: int = 0
    fixed: int = 0
    regressions: int = 0
    new_issues: int = 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AuditStats):
            return False
        return (
            self.active_issues == other.active_issues
            and self.exceptions == other.exceptions
            and self.fixed == other.fixed
            and self.regressions == other.regressions
        )


class StatsAssertions:
    """
    Statistics consistency verification.

    Ensures CLI output, Cover sheet, and DB all report same numbers.
    """

    @staticmethod
    def parse_cli_stats(output: str) -> AuditStats:
        """
        Parse statistics from CLI sync output.

        Expected format:
            Fixed: 3
            Regressions: 0
            ...
        """
        stats = AuditStats()

        patterns = {
            "fixed": r"Fixed:\s*(\d+)",
            "regressions": r"Regressions?:\s*(\d+)",
            "new_issues": r"New Issues?:\s*(\d+)",
            "exceptions": r"Exceptions?:\s*(\d+)",
            "active_issues": r"Active Issues?:\s*(\d+)",
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                setattr(stats, field, int(match.group(1)))

        return stats

    @staticmethod
    def get_cover_sheet_stats(wb: Workbook) -> AuditStats:
        """
        Extract statistics from Cover sheet.

        Cover sheet has summary stats in specific cells.
        """
        stats = AuditStats()

        if "Cover" not in wb.sheetnames:
            return stats

        ws = wb["Cover"]

        # Search for stats in cover sheet
        # Format varies, so we search for labels
        for row in ws.iter_rows(min_row=1, max_row=50):
            for i, cell in enumerate(row):
                if cell.value and isinstance(cell.value, str):
                    label = cell.value.lower()
                    # Get the value from next cell
                    if i + 1 < len(row):
                        value = row[i + 1].value
                        if isinstance(value, (int, float)):
                            if "active" in label and "issue" in label:
                                stats.active_issues = int(value)
                            elif "exception" in label:
                                stats.exceptions = int(value)
                            elif "fixed" in label:
                                stats.fixed = int(value)
                            elif "regression" in label:
                                stats.regressions = int(value)

        return stats

    @staticmethod
    def get_db_stats(conn: sqlite3.Connection, run_id: int) -> AuditStats:
        """
        Get statistics from database action_log.

        Args:
            conn: SQLite connection
            run_id: Audit run ID
        """
        stats = AuditStats()

        cursor = conn.execute(
            """
            SELECT action_type, COUNT(*) as count
            FROM action_log
            WHERE sync_run_id = ?
            GROUP BY action_type
        """,
            (run_id,),
        )

        for row in cursor:
            action_type = row[0].lower() if row[0] else ""
            count = row[1]

            if "fixed" in action_type:
                stats.fixed = count
            elif "regression" in action_type:
                stats.regressions = count
            elif "exception" in action_type and "documented" in action_type:
                stats.exceptions = count
            elif "new" in action_type:
                stats.new_issues = count

        return stats

    @staticmethod
    def assert_stats_match(
        cli_stats: AuditStats,
        excel_stats: AuditStats | None = None,
        db_stats: AuditStats | None = None,
    ) -> None:
        """
        Assert statistics match across all sources.
        """
        sources = {"CLI": cli_stats}
        if excel_stats:
            sources["Excel"] = excel_stats
        if db_stats:
            sources["DB"] = db_stats

        # Compare all pairs
        keys = list(sources.keys())
        for i, key1 in enumerate(keys):
            for key2 in keys[i + 1 :]:
                s1, s2 = sources[key1], sources[key2]
                assert s1 == s2, (
                    f"Stats mismatch between {key1} and {key2}:\n"
                    f"  {key1}: fixed={s1.fixed}, reg={s1.regressions}, exc={s1.exceptions}\n"
                    f"  {key2}: fixed={s2.fixed}, reg={s2.regressions}, exc={s2.exceptions}"
                )
