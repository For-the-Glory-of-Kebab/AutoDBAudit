"""
Database Inspector for E2E Tests.
Verifies the state of the SQLite audit history.
"""

import sqlite3
from pathlib import Path


class DbInspector:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_finding_status(self, entity_key: str) -> str:
        """Get the current status of a finding in the latest run."""
        conn = self._get_conn()
        try:
            # Get latest run
            run = conn.execute(
                "SELECT id FROM audit_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not run:
                return None

            # Get finding
            # Note: Entity Key construction varies.
            # We assume loose matching on the key for robustness.
            rows = conn.execute(
                "SELECT status FROM findings WHERE audit_run_id = ? AND entity_key LIKE ?",
                (run["id"], f"%{entity_key}%"),
            ).fetchall()

            if not rows:
                return None
            return rows[0]["status"]
        finally:
            conn.close()

    def get_action_logs(self, entity_key: str = None) -> list[dict]:
        """Get action logs, optionally filtered by entity."""
        conn = self._get_conn()
        try:
            sql = "SELECT * FROM action_log"
            params = []
            if entity_key:
                sql += " WHERE entity_key LIKE ?"
                params.append(f"%{entity_key}%")

            sql += " ORDER BY captured_at ASC, id ASC"

            rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_latest_action_type(self, entity_key: str) -> str:
        logs = self.get_action_logs(entity_key)
        if not logs:
            return None
        # Assuming ID order is chronological
        return logs[-1]["action_type"]

    def count_active_exceptions(self) -> int:
        # This is a bit complex as it depends on status='Exception' in findings
        # OR just counting 'findings' where status='Exception' in latest run
        conn = self._get_conn()
        try:
            run = conn.execute(
                "SELECT id FROM audit_runs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            if not run:
                return 0
            count = conn.execute(
                "SELECT count(*) as c FROM findings WHERE audit_run_id = ? AND status = 'Exception'",
                (run["id"],),
            ).fetchone()
            return count["c"]
        finally:
            conn.close()
