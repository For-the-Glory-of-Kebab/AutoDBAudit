"""
Finalize service for diff-based remediation verification.

Core workflow:
1. Re-runs audit (creates new audit_run)
2. Compares new findings to baseline
3. Detects what changed:
   - FAIL→PASS = Fixed (auto-log action)
   - FAIL→FAIL = Still failing (exception or retry)
   - PASS→FAIL = Regression (new finding)
4. Records changes in finding_changes table
5. Updates Actions sheet in Excel

This is the KEY feature - verifies remediation without parsing TSQL scripts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.application.audit_service import AuditService

logger = logging.getLogger(__name__)


class FinalizeService:
    """
    Service for finalizing audit after remediation.
    
    Workflow:
    1. finalize(baseline_run_id) - Re-audit and compare
    2. Returns summary of fixed/excepted/regression
    3. Updates finding_changes table
    """
    
    def __init__(
        self,
        db_path: str | Path = "output/audit_history.db",
    ):
        """
        Initialize finalize service.
        
        Args:
            db_path: Path to SQLite audit database
        """
        self.db_path = Path(db_path)
        logger.info("FinalizeService initialized")
    
    def get_latest_run_id(self) -> int | None:
        """Get the most recent audit run ID."""
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            "SELECT id FROM audit_runs ORDER BY started_at DESC LIMIT 1"
        ).fetchone()
        conn.close()
        return row[0] if row else None
    
    def finalize(
        self,
        baseline_run_id: int | None = None,
        audit_service: "AuditService" = None,
        targets_file: str = "sql_targets.json",
    ) -> dict:
        """
        Finalize remediation by re-auditing and comparing.
        
        Args:
            baseline_run_id: Baseline audit to compare against (latest if None)
            audit_service: AuditService instance (creates new if None)
            targets_file: Targets config for re-audit
            
        Returns:
            Dict with 'fixed', 'excepted', 'regression', 'new' counts
        """
        import sqlite3
        from autodbaudit.infrastructure.sqlite.schema import compare_findings
        
        # Get baseline run ID
        if baseline_run_id is None:
            baseline_run_id = self.get_latest_run_id()
            if baseline_run_id is None:
                logger.error("No baseline audit found. Run --audit first.")
                return {"error": "No baseline audit found"}
        
        logger.info("Finalize: baseline run ID = %d", baseline_run_id)
        
        # Run new audit
        logger.info("Finalize: Running re-audit...")
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
        
        # Get new run ID
        new_run_id = self.get_latest_run_id()
        if new_run_id == baseline_run_id:
            logger.error("Re-audit did not create new run")
            return {"error": "Re-audit did not create new run"}
        
        logger.info("Finalize: new run ID = %d", new_run_id)
        
        # Compare findings
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        diff = compare_findings(conn, baseline_run_id, new_run_id)
        
        # Record changes
        now = datetime.now(timezone.utc).isoformat()
        
        for item in diff["fixed"]:
            self._record_change(
                conn, baseline_run_id, new_run_id,
                item["old"]["entity_key"],
                "fixed",
                item["old"]["status"],
                item["new"]["status"],
                self._generate_action_desc(item["old"]),
                now
            )
        
        for item in diff["excepted"]:
            self._record_change(
                conn, baseline_run_id, new_run_id,
                item["old"]["entity_key"],
                "excepted",
                item["old"]["status"],
                item["new"]["status"],
                None,  # No action taken
                now
            )
        
        for item in diff["regression"]:
            self._record_change(
                conn, baseline_run_id, new_run_id,
                item["old"]["entity_key"],
                "regression",
                item["old"]["status"],
                item["new"]["status"],
                None,
                now
            )
        
        for item in diff["new"]:
            self._record_change(
                conn, baseline_run_id, new_run_id,
                item["new"]["entity_key"],
                "new",
                None,
                item["new"]["status"],
                None,
                now
            )
        
        conn.close()
        
        # Summary
        result = {
            "baseline_run_id": baseline_run_id,
            "new_run_id": new_run_id,
            "fixed": len(diff["fixed"]),
            "excepted": len(diff["excepted"]),
            "regression": len(diff["regression"]),
            "new": len(diff["new"]),
        }
        
        logger.info(
            "Finalize complete: %d fixed, %d excepted, %d regression, %d new",
            result["fixed"], result["excepted"], result["regression"], result["new"]
        )
        
        return result
    
    def _record_change(
        self,
        conn,
        from_run_id: int,
        to_run_id: int,
        entity_key: str,
        change_type: str,
        old_status: str | None,
        new_status: str | None,
        action_desc: str | None,
        timestamp: str,
    ) -> None:
        """Record a finding change."""
        conn.execute("""
            INSERT OR REPLACE INTO finding_changes
            (from_run_id, to_run_id, entity_key, change_type, 
             old_status, new_status, action_description, changed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            from_run_id, to_run_id, entity_key, change_type,
            old_status, new_status, action_desc, timestamp
        ))
        conn.commit()
    
    def _generate_action_desc(self, finding: dict) -> str:
        """Generate action description for a fixed finding."""
        ft = finding["finding_type"]
        entity = finding["entity_name"]
        
        templates = {
            "sa_account": f"Disabled SA account",
            "config": f"Set {entity} to compliant value",
            "login": f"Disabled/secured login '{entity}'",
            "database": f"Disabled TRUSTWORTHY on '{entity}'",
            "db_user": f"Removed/fixed user in {entity}",
            "linked_server": f"Secured linked server '{entity}'",
            "backup": f"Created backup for '{entity}'",
        }
        
        return templates.get(ft, f"Fixed {ft}: {entity}")
    
    def get_summary(self, from_run_id: int, to_run_id: int) -> dict:
        """Get summary of changes between two runs."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute("""
            SELECT change_type, COUNT(*) as count
            FROM finding_changes
            WHERE from_run_id = ? AND to_run_id = ?
            GROUP BY change_type
        """, (from_run_id, to_run_id)).fetchall()
        
        conn.close()
        
        return {row["change_type"]: row["count"] for row in rows}


def main():
    """CLI entry point for finalize."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Finalize remediation")
    parser.add_argument("--db", default="output/audit_history.db", help="Audit database path")
    parser.add_argument("--baseline", type=int, help="Baseline run ID (latest if not specified)")
    parser.add_argument("--targets", default="sql_targets.json", help="Targets config")
    
    args = parser.parse_args()
    
    service = FinalizeService(db_path=args.db)
    result = service.finalize(baseline_run_id=args.baseline, targets_file=args.targets)
    
    if "error" in result:
        print(f"❌ {result['error']}")
        return 1
    
    print(f"\n✅ Finalize complete!")
    print(f"   Baseline: Run #{result['baseline_run_id']}")
    print(f"   New:      Run #{result['new_run_id']}")
    print(f"")
    print(f"   ✅ Fixed:      {result['fixed']}")
    print(f"   ⚠️ Excepted:   {result['excepted']}")
    print(f"   🔴 Regression: {result['regression']}")
    print(f"   🆕 New:        {result['new']}")
    
    return 0


if __name__ == "__main__":
    exit(main())
