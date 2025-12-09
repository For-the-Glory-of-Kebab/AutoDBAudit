"""
Finalize service for completing an audit cycle.

This is the "commit" step - makes the audit permanent in SQLite.

Workflow:
1. Read Excel annotations (Notes/Reason/etc.)
2. Persist annotations to SQLite
3. Get action_log summary from SyncService
4. Mark audit run as 'finalized'
5. DB becomes complete source of truth

After finalization, the audit is reproducible from SQLite alone.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class FinalizeService:
    """
    Service for finalizing an audit cycle.
    
    This is different from SyncService:
    - SyncService: Repeatable, tracks progress
    - FinalizeService: One-time, commits everything to DB
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
    
    def finalize(
        self,
        excel_path: str | Path | None = None,
        baseline_run_id: int | None = None,
    ) -> dict:
        """
        Finalize the audit cycle.
        
        1. Read annotations from Excel
        2. Persist to SQLite
        3. Get action_log summary
        4. Mark baseline run as finalized
        
        Args:
            excel_path: Excel file with annotations (latest if None)
            baseline_run_id: Baseline run to finalize (first if None)
            
        Returns:
            Dict with summary counts and status
        """
        import sqlite3
        from autodbaudit.application.exception_service import ExceptionService
        from autodbaudit.application.sync_service import SyncService
        
        # Get baseline run ID
        if baseline_run_id is None:
            baseline_run_id = self.get_initial_run_id()
            if baseline_run_id is None:
                logger.error("No baseline audit found. Run --audit first.")
                return {"error": "No baseline audit found"}
        
        logger.info("Finalize: baseline run ID = %d", baseline_run_id)
        
        # Step 1: Read Excel annotations
        logger.info("Finalize: Reading Excel annotations...")
        exception_service = ExceptionService(
            db_path=self.db_path,
            excel_path=excel_path
        )
        annotation_result = exception_service.apply_exceptions(
            audit_run_id=baseline_run_id
        )
        
        if "error" in annotation_result:
            logger.warning("Annotation reading failed: %s", annotation_result["error"])
            annotations_applied = 0
        else:
            annotations_applied = annotation_result.get("applied", 0)
        
        logger.info("Finalize: Applied %d annotations", annotations_applied)
        
        # Step 2: Get action_log summary
        logger.info("Finalize: Getting action summary...")
        sync_service = SyncService(db_path=self.db_path)
        action_summary = sync_service.get_action_summary(baseline_run_id)
        
        # Step 3: Mark as finalized
        logger.info("Finalize: Marking audit as finalized...")
        conn = sqlite3.connect(self.db_path)
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute("""
            UPDATE audit_runs 
            SET status = 'finalized', completed_at = ?
            WHERE id = ?
        """, (now, baseline_run_id))
        conn.commit()
        conn.close()
        
        # Build result
        result = {
            "baseline_run_id": baseline_run_id,
            "status": "finalized",
            "annotations_applied": annotations_applied,
            "actions": action_summary if "error" not in action_summary else {},
        }
        
        logger.info(
            "Finalize complete: run #%d finalized, %d annotations applied",
            baseline_run_id, annotations_applied
        )
        
        return result
    
    def get_finalized_runs(self) -> list[dict]:
        """Get all finalized audit runs."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        rows = conn.execute("""
            SELECT id, started_at, completed_at, report_path
            FROM audit_runs
            WHERE status = 'finalized'
            ORDER BY started_at DESC
        """).fetchall()
        
        conn.close()
        
        return [dict(row) for row in rows]


def main():
    """CLI entry point for finalize."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Finalize audit cycle")
    parser.add_argument("--db", default="output/audit_history.db")
    parser.add_argument("--excel", help="Excel file with annotations")
    parser.add_argument("--baseline", type=int, help="Baseline run ID (first if not specified)")
    parser.add_argument("--list", action="store_true", help="List finalized audits")
    
    args = parser.parse_args()
    
    service = FinalizeService(db_path=args.db)
    
    if args.list:
        runs = service.get_finalized_runs()
        print(f"\nFinalized Audits: {len(runs)}")
        for run in runs:
            print(f"  Run #{run['id']}: {run['started_at']}")
        return 0
    
    result = service.finalize(
        excel_path=args.excel,
        baseline_run_id=args.baseline
    )
    
    if "error" in result:
        print(f"❌ {result['error']}")
        return 1
    
    print("\n✅ Audit Finalized!")
    print(f"   Run ID: #{result['baseline_run_id']}")
    print(f"   Annotations: {result['annotations_applied']}")
    print("")
    if result["actions"]:
        print("   Actions:")
        for action_type, count in result["actions"].items():
            print(f"      {action_type}: {count}")
    
    return 0


if __name__ == "__main__":
    exit(main())
