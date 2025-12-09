"""
Status service for audit dashboard.

Shows a summary of the current audit state from SQLite:
- Latest audit run info
- Counts by table (logins, databases, findings, etc.)
- Action log summary
- Pending items
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class StatusService:
    """Service for displaying audit status dashboard."""
    
    def __init__(self, db_path: str | Path = "output/audit_history.db"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def get_status(self) -> dict:
        """Get comprehensive audit status."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        status = {}
        
        # Latest audit run
        run = conn.execute("""
            SELECT id, started_at, ended_at, status
            FROM audit_runs ORDER BY started_at DESC LIMIT 1
        """).fetchone()
        
        if run:
            status["latest_run"] = {
                "id": run["id"],
                "started_at": run["started_at"],
                "status": run["status"] or "in_progress",
                "run_type": "audit",
            }
            run_id = run["id"]
        else:
            status["latest_run"] = None
            conn.close()
            return status
        
        # Counts by table
        tables = [
            ("servers", "Servers"),
            ("instances", "Instances"),
            ("logins", "Logins"),
            ("databases", "Databases"),
            ("database_users", "Database Users"),
            ("config_settings", "Config Settings"),
            ("linked_servers", "Linked Servers"),
            ("backup_history", "Backups"),
            ("findings", "Findings"),
        ]
        
        counts = {}
        for table, label in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
                counts[label] = row["cnt"]
            except Exception:
                counts[label] = 0
        
        status["counts"] = counts
        
        # Findings by status
        findings = conn.execute("""
            SELECT status, COUNT(*) as cnt
            FROM findings
            WHERE audit_run_id = ?
            GROUP BY status
        """, (run_id,)).fetchall()
        
        status["findings_by_status"] = {row["status"]: row["cnt"] for row in findings}
        
        # Findings by type
        findings_type = conn.execute("""
            SELECT finding_type, COUNT(*) as cnt
            FROM findings
            WHERE audit_run_id = ?
            GROUP BY finding_type
        """, (run_id,)).fetchall()
        
        status["findings_by_type"] = {row["finding_type"]: row["cnt"] for row in findings_type}
        
        # Action log summary (if any syncs done)
        try:
            actions = conn.execute("""
                SELECT action_type, COUNT(*) as cnt
                FROM action_log
                GROUP BY action_type
            """).fetchall()
            status["actions"] = {row["action_type"]: row["cnt"] for row in actions}
        except Exception:
            status["actions"] = {}
        
        # Annotations count
        try:
            ann = conn.execute("SELECT COUNT(*) as cnt FROM annotations").fetchone()
            status["annotations"] = ann["cnt"]
        except Exception:
            status["annotations"] = 0
        
        conn.close()
        return status
    
    def print_status(self) -> None:
        """Print formatted status to console."""
        status = self.get_status()
        
        print("\n" + "=" * 50)
        print("📊 AUDIT STATUS DASHBOARD")
        print("=" * 50)
        
        # Latest run
        if not status.get("latest_run"):
            print("\n❌ No audit runs found. Run --audit first.")
            return
        
        run = status["latest_run"]
        print(f"\n🔍 Latest Run: #{run['id']}")
        print(f"   Started: {run['started_at']}")
        print(f"   Status:  {run['status']}")
        print(f"   Type:    {run['run_type']}")
        
        # Counts
        print("\n📦 Data Collected:")
        for label, cnt in status.get("counts", {}).items():
            print(f"   {label}: {cnt}")
        
        # Findings summary
        if status.get("findings_by_status"):
            print("\n🔎 Findings by Status:")
            for st, cnt in status["findings_by_status"].items():
                icon = "✅" if st == "PASS" else "❌" if st == "FAIL" else "⚠️"
                print(f"   {icon} {st}: {cnt}")
        
        if status.get("findings_by_type"):
            print("\n📋 Findings by Type:")
            for ft, cnt in status["findings_by_type"].items():
                print(f"   {ft}: {cnt}")
        
        # Actions
        if status.get("actions"):
            print("\n🔧 Action Log:")
            for action, cnt in status["actions"].items():
                print(f"   {action}: {cnt}")
        
        # Annotations
        if status.get("annotations"):
            print(f"\n📝 Annotations: {status['annotations']}")
        
        print("\n" + "=" * 50)


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Audit status dashboard")
    parser.add_argument("--db", default="output/audit_history.db")
    
    args = parser.parse_args()
    
    try:
        service = StatusService(db_path=args.db)
        service.print_status()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
