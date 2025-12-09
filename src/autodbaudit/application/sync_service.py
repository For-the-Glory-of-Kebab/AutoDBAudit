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
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.application.audit_service import AuditService

logger = logging.getLogger(__name__)


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
        logger.info("SyncService initialized")
    
    def get_initial_run_id(self) -> int | None:
        """Get the first (baseline) audit run ID."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT id FROM audit_runs WHERE run_type = 'audit' ORDER BY started_at ASC LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else None
    
    def get_latest_run_id(self) -> int | None:
        """Get the most recent audit run ID."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT id FROM audit_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else None
    
    def sync(
        self,
        audit_service: "AuditService" = None,
        targets_file: str = "sql_targets.json",
    ) -> dict:
        """
        Sync remediation progress.
        
        1. Re-audit current state (creates new audit_run with type='sync')
        2. Diff against initial baseline
        3. Update action_log with real timestamps
        
        Args:
            audit_service: AuditService instance (creates new if None)
            targets_file: Targets config for re-audit
            
        Returns:
            Dict with 'fixed', 'still_failing', 'regression', 'new' counts
        """
        import sqlite3
        
        # Get initial baseline
        initial_run_id = self.get_initial_run_id()
        if initial_run_id is None:
            logger.error("No baseline audit found. Run --audit first.")
            return {"error": "No baseline audit found"}
        
        logger.info("Sync: initial baseline run ID = %d", initial_run_id)
        
        # Run new audit
        logger.info("Sync: Running re-audit...")
        if audit_service is None:
            from autodbaudit.application.audit_service import AuditService
            audit_service = AuditService(
                config_dir=Path("config"),
                output_dir=Path("output")
            )
        
        try:
            audit_service.run_audit(targets_file=targets_file)
        except Exception as e:
            logger.error("Re-audit failed: %s", e)
            return {"error": f"Re-audit failed: {e}"}
        
        # Get new run ID and mark as sync type
        current_run_id = self.get_latest_run_id()
        if current_run_id == initial_run_id:
            logger.error("Re-audit did not create new run")
            return {"error": "Re-audit did not create new run"}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Mark as sync run
        conn.execute(
            "UPDATE audit_runs SET run_type = 'sync' WHERE id = ?",
            (current_run_id,)
        )
        conn.commit()
        
        logger.info("Sync: current run ID = %d", current_run_id)
        
        # Compare findings
        result = self._update_action_log(
            conn, initial_run_id, current_run_id
        )
        
        conn.close()
        
        result["initial_run_id"] = initial_run_id
        result["current_run_id"] = current_run_id
        
        logger.info(
            "Sync complete: %d fixed, %d still_failing, %d regression, %d new",
            result["fixed"], result["still_failing"], 
            result["regression"], result["new"]
        )
        
        return result
    
    def _update_action_log(
        self,
        conn,
        initial_run_id: int,
        current_run_id: int,
    ) -> dict:
        """
        Update action_log based on diff.
        
        Key behavior:
        - NEW fixes get today's timestamp
        - EXISTING fixes keep original timestamp
        - All get updated last_sync_run_id
        """
        from autodbaudit.infrastructure.sqlite.schema import get_findings_for_run
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Get findings from both runs
        initial_findings = {
            f["entity_key"]: f 
            for f in get_findings_for_run(conn, initial_run_id)
        }
        current_findings = {
            f["entity_key"]: f 
            for f in get_findings_for_run(conn, current_run_id)
        }
        
        # Get existing action_log entries
        existing_actions = {}
        for row in conn.execute(
            "SELECT entity_key, action_type, action_date FROM action_log WHERE initial_run_id = ?",
            (initial_run_id,)
        ).fetchall():
            existing_actions[row[0]] = {
                "action_type": row[1],
                "action_date": row[2]
            }
        
        counts = {"fixed": 0, "still_failing": 0, "regression": 0, "new": 0}
        
        # Process each initial finding
        for key, initial in initial_findings.items():
            if key in current_findings:
                current = current_findings[key]
                
                if initial["status"] in ("FAIL", "WARN") and current["status"] == "PASS":
                    # FIXED
                    self._upsert_action(
                        conn, initial_run_id, key, initial["finding_type"],
                        "fixed", now, existing_actions,
                        f"Fixed: {initial['finding_type']} - {initial['entity_name']}",
                        current_run_id
                    )
                    counts["fixed"] += 1
                    
                elif initial["status"] in ("FAIL", "WARN") and current["status"] in ("FAIL", "WARN"):
                    # STILL FAILING (potential exception)
                    self._upsert_action(
                        conn, initial_run_id, key, initial["finding_type"],
                        "still_failing", now, existing_actions,
                        None,  # No action description for still failing
                        current_run_id
                    )
                    counts["still_failing"] += 1
                    
                elif initial["status"] == "PASS" and current["status"] in ("FAIL", "WARN"):
                    # REGRESSION
                    self._upsert_action(
                        conn, initial_run_id, key, current["finding_type"],
                        "regression", now, existing_actions,
                        f"Regression: {current['finding_type']} - {current['entity_name']}",
                        current_run_id
                    )
                    counts["regression"] += 1
        
        # New findings (didn't exist in initial)
        for key, current in current_findings.items():
            if key not in initial_findings and current["status"] in ("FAIL", "WARN"):
                self._upsert_action(
                    conn, initial_run_id, key, current["finding_type"],
                    "new", now, existing_actions,
                    f"New finding: {current['finding_type']} - {current['entity_name']}",
                    current_run_id
                )
                counts["new"] += 1
        
        conn.commit()
        return counts
    
    def _upsert_action(
        self,
        conn,
        initial_run_id: int,
        entity_key: str,
        finding_type: str,
        action_type: str,
        now: str,
        existing_actions: dict,
        action_description: str | None,
        current_run_id: int,
    ) -> None:
        """
        Insert or update action_log entry.
        
        Key: Preserve original action_date for existing entries.
        """
        if entity_key in existing_actions:
            # UPDATE: preserve original action_date
            conn.execute("""
                UPDATE action_log 
                SET action_type = ?, action_description = COALESCE(?, action_description),
                    last_sync_run_id = ?
                WHERE initial_run_id = ? AND entity_key = ?
            """, (action_type, action_description, current_run_id,
                  initial_run_id, entity_key))
        else:
            # INSERT: set action_date to NOW
            conn.execute("""
                INSERT INTO action_log
                (initial_run_id, entity_key, finding_type, action_type, 
                 action_date, action_description, captured_at, last_sync_run_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (initial_run_id, entity_key, finding_type, action_type,
                  now, action_description, now, current_run_id))
    
    def get_action_summary(self, initial_run_id: int | None = None) -> dict:
        """Get summary of all actions for an audit cycle."""
        import sqlite3
        
        if initial_run_id is None:
            initial_run_id = self.get_initial_run_id()
        
        if initial_run_id is None:
            return {"error": "No baseline found"}
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute("""
            SELECT action_type, COUNT(*) as count
            FROM action_log
            WHERE initial_run_id = ?
            GROUP BY action_type
        """, (initial_run_id,)).fetchall()
        
        conn.close()
        
        return {row["action_type"]: row["count"] for row in rows}
    
    def get_actions(self, initial_run_id: int | None = None) -> list[dict]:
        """Get all actions for an audit cycle."""
        import sqlite3
        
        if initial_run_id is None:
            initial_run_id = self.get_initial_run_id()
        
        if initial_run_id is None:
            return []
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute("""
            SELECT * FROM action_log
            WHERE initial_run_id = ?
            ORDER BY action_date, entity_key
        """, (initial_run_id,)).fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]


def main():
    """CLI entry point for sync."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sync remediation progress")
    parser.add_argument("--db", default="output/audit_history.db")
    parser.add_argument("--targets", default="sql_targets.json")
    parser.add_argument("--summary", action="store_true", help="Show action summary only")
    
    args = parser.parse_args()
    
    service = SyncService(db_path=args.db)
    
    if args.summary:
        summary = service.get_action_summary()
        if "error" in summary:
            print(f"❌ {summary['error']}")
            return 1
        print(f"\n📊 Action Summary:")
        for action_type, count in summary.items():
            print(f"   {action_type}: {count}")
        return 0
    
    result = service.sync(targets_file=args.targets)
    
    if "error" in result:
        print(f"❌ {result['error']}")
        return 1
    
    print(f"\n✅ Sync complete!")
    print(f"   Baseline: Run #{result['initial_run_id']}")
    print(f"   Current:  Run #{result['current_run_id']}")
    print(f"")
    print(f"   ✅ Fixed:         {result['fixed']}")
    print(f"   ⚠️  Still Failing: {result['still_failing']}")
    print(f"   🔴 Regression:    {result['regression']}")
    print(f"   🆕 New:           {result['new']}")
    
    return 0


if __name__ == "__main__":
    exit(main())
