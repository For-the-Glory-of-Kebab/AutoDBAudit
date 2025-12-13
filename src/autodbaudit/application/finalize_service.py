"""
Finalize service for completing an audit cycle.

This is the "commit" step - makes the audit permanent in SQLite.

FINALIZATION RULES:
1. Cannot finalize if there are outstanding FAIL findings without exceptions
2. Cannot finalize if there are outstanding WARN findings without notes
3. Use --force to bypass these checks (not recommended)
4. Finalization is PERMANENT - creates archive and locks the audit

Workflow:
1. Pre-flight checks (outstanding issues)
2. Read Excel annotations (Notes/Reason/etc.)
3. Persist annotations to SQLite
4. Get action_log summary from SyncService
5. Archive final Excel report
6. Mark audit run as 'finalized'
7. DB becomes complete source of truth

After finalization, the audit is reproducible from SQLite alone.
"""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class FinalizeResult:
    """Result of finalization attempt."""
    success: bool
    baseline_run_id: int | None
    annotations_applied: int
    actions: dict
    outstanding_fails: int
    outstanding_warns: int
    blocked: bool
    block_reason: str | None
    archive_path: Path | None


class FinalizeService:
    """
    Service for finalizing an audit cycle.
    
    This is different from SyncService:
    - SyncService: Repeatable, tracks progress
    - FinalizeService: One-time, commits everything to DB
    
    Finalization enforces:
    - No unresolved FAIL findings (must be fixed or excepted)
    - No unresolved WARN findings (must have notes or be excepted)
    - Creates final archive of Excel report
    - Marks audit as permanently complete
    """
    
    def __init__(
        self,
        db_path: str | Path = "output/audit_history.db",
        output_dir: str | Path = "output",
    ):
        """
        Initialize finalize service.
        
        Args:
            db_path: Path to SQLite audit database
            output_dir: Base output directory
        """
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
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
    
    def check_outstanding_issues(
        self, baseline_run_id: int
    ) -> tuple[list[dict], list[dict]]:
        """
        Check for outstanding FAIL and WARN findings.
        
        A finding is considered "resolved" if:
        - Status changed to PASS (fixed)
        - Has an exception in action_log with approved status
        - Has annotation with exception reason
        
        Returns:
            Tuple of (outstanding_fails, outstanding_warns)
        """
        import sqlite3
        from autodbaudit.infrastructure.sqlite.schema import get_findings_for_run
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Get latest run for current state
        latest_run_id = self.get_latest_run_id()
        if latest_run_id is None:
            conn.close()
            return [], []
        
        # Get findings from latest run
        all_findings = get_findings_for_run(conn, latest_run_id)
        
        # Get existing actions (to check if excepted)
        action_log = conn.execute(
            """
            SELECT entity_key, action_type, exception_reason
            FROM action_log
            WHERE initial_run_id = ?
        """,
            (baseline_run_id,),
        ).fetchall()
        
        excepted_keys = set()
        for row in action_log:
            if row["action_type"] in ("excepted", "fixed"):
                excepted_keys.add(row["entity_key"])
            # Also check if it has exception reason
            if row["exception_reason"]:
                excepted_keys.add(row["entity_key"])
        
        # Get annotations with exceptions
        try:
            annotations = conn.execute(
                """
                SELECT entity_key FROM annotations
                WHERE exception_reason IS NOT NULL AND exception_reason != ''
            """
            ).fetchall()
            for row in annotations:
                excepted_keys.add(row["entity_key"])
        except Exception:
            pass  # annotations table might not exist
        
        conn.close()
        
        # Filter to outstanding issues
        outstanding_fails = []
        outstanding_warns = []
        
        for f in all_findings:
            key = f["entity_key"]
            status = f["status"]
            
            # Skip if already resolved/excepted
            if key in excepted_keys:
                continue
            
            if status == "FAIL":
                outstanding_fails.append(f)
            elif status == "WARN":
                outstanding_warns.append(f)
        
        return outstanding_fails, outstanding_warns
    
    def finalize(
        self,
        excel_path: str | Path | None = None,
        baseline_run_id: int | None = None,
        force: bool = False,
        audit_manager=None,
        audit_id: int | None = None,
    ) -> dict:
        """
        Finalize the audit cycle.
        
        1. Pre-flight checks for outstanding issues
        2. Read annotations from Excel
        3. Persist to SQLite
        4. Get action_log summary
        5. Archive final report
        6. Mark baseline run as finalized
        
        Args:
            excel_path: Excel file with annotations (latest if None)
            baseline_run_id: Baseline run to finalize (first if None)
            force: Bypass safety checks (not recommended)
            audit_manager: Optional AuditManager for paths
            audit_id: Optional Audit ID context
            
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
        
        # Check if already finalized
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        run_status = conn.execute(
            "SELECT status FROM audit_runs WHERE id = ?", (baseline_run_id,)
        ).fetchone()
        
        if run_status and run_status["status"] == "finalized":
            conn.close()
            return {"error": f"Audit run #{baseline_run_id} is already finalized"}
        
        conn.close()
        
        # =====================================================================
        # PRE-FLIGHT CHECKS
        # =====================================================================
        logger.info("Finalize: Running pre-flight checks...")
        
        outstanding_fails, outstanding_warns = self.check_outstanding_issues(
            baseline_run_id
        )
        
        blockers = []
        
        if outstanding_fails:
            blockers.append(
                f"{len(outstanding_fails)} FAIL finding(s) without fix or exception"
            )
        
        if outstanding_warns:
            blockers.append(
                f"{len(outstanding_warns)} WARN finding(s) without resolution"
            )
        
        if blockers and not force:
            # Build detailed error message
            error_lines = ["Cannot finalize - outstanding issues:"]
            error_lines.extend([f"  • {b}" for b in blockers])
            error_lines.append("")
            error_lines.append("Options:")
            error_lines.append("  1. Fix the issues and run --sync")
            error_lines.append("  2. Add exceptions in Excel and run --apply-exceptions")
            error_lines.append("  3. Use --force to finalize anyway (not recommended)")
            
            # Show first few outstanding items
            if outstanding_fails:
                error_lines.append("")
                error_lines.append("Outstanding FAIL findings:")
                for f in outstanding_fails[:5]:
                    error_lines.append(f"  ❌ {f['finding_type']}: {f['entity_name']}")
                if len(outstanding_fails) > 5:
                    error_lines.append(f"  ... and {len(outstanding_fails) - 5} more")
            
            if outstanding_warns:
                error_lines.append("")
                error_lines.append("Outstanding WARN findings:")
                for f in outstanding_warns[:5]:
                    error_lines.append(f"  ⚠️  {f['finding_type']}: {f['entity_name']}")
                if len(outstanding_warns) > 5:
                    error_lines.append(f"  ... and {len(outstanding_warns) - 5} more")
            
            return {
                "error": "\n".join(error_lines),
                "outstanding_fails": len(outstanding_fails),
                "outstanding_warns": len(outstanding_warns),
                "blocked": True,
            }
        
        if blockers and force:
            logger.warning(
                "Finalizing with --force despite %d FAIL and %d WARN findings",
                len(outstanding_fails),
                len(outstanding_warns),
            )
            print(
                f"\n⚠️  WARNING: Finalizing with {len(outstanding_fails)} FAIL "
                f"and {len(outstanding_warns)} WARN findings (--force used)"
            )
        
        # =====================================================================
        # STEP 1: Read Excel annotations
        # =====================================================================
        logger.info("Finalize: Reading Excel annotations...")
        
        # Determine Excel path
        if excel_path is None:
            if audit_manager and audit_id:
                excel_path = audit_manager.get_latest_excel_path(audit_id)
            else:
                excel_path = self.output_dir / "Audit_Latest.xlsx"
        
        excel_path = Path(excel_path) if excel_path else None
        
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
        
        # =====================================================================
        # STEP 2: Get action_log summary
        # =====================================================================
        logger.info("Finalize: Getting action summary...")
        sync_service = SyncService(db_path=self.db_path)
        action_summary = sync_service.get_action_summary(baseline_run_id)
        
        # =====================================================================
        # STEP 3: Archive final Excel report
        # =====================================================================
        archive_path = None
        if excel_path and excel_path.exists():
            logger.info("Finalize: Creating final archive...")
            
            # Determine archive location
            if audit_manager and audit_id:
                audit_folder = audit_manager._get_audit_folder(audit_id)
                archive_dir = audit_folder / "finalized"
            else:
                archive_dir = self.output_dir / "finalized"
            
            archive_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"sql_audit_final_{baseline_run_id}_{timestamp}.xlsx"
            archive_path = archive_dir / archive_name
            
            try:
                shutil.copy(excel_path, archive_path)
                logger.info("Archived to: %s", archive_path)
            except Exception as e:
                logger.warning("Could not create archive: %s", e)
        
        # =====================================================================
        # STEP 4: Mark as finalized in database
        # =====================================================================
        logger.info("Finalize: Marking audit as finalized...")
        conn = sqlite3.connect(self.db_path)
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute("""
            UPDATE audit_runs 
            SET status = 'finalized', completed_at = ?, report_path = ?
            WHERE id = ?
        """, (now, str(archive_path) if archive_path else None, baseline_run_id))
        conn.commit()
        conn.close()
        
        # =====================================================================
        # BUILD RESULT
        # =====================================================================
        result = {
            "baseline_run_id": baseline_run_id,
            "status": "finalized",
            "annotations_applied": annotations_applied,
            "actions": action_summary if "error" not in action_summary else {},
            "outstanding_fails": len(outstanding_fails),
            "outstanding_warns": len(outstanding_warns),
            "forced": force and (outstanding_fails or outstanding_warns),
            "archive_path": str(archive_path) if archive_path else None,
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
    
    def get_finalization_status(self, baseline_run_id: int | None = None) -> dict:
        """
        Get status of what would happen if finalize is called.
        
        Useful for previewing before actual finalization.
        """
        if baseline_run_id is None:
            baseline_run_id = self.get_initial_run_id()
        
        if baseline_run_id is None:
            return {"error": "No baseline audit found"}
        
        outstanding_fails, outstanding_warns = self.check_outstanding_issues(
            baseline_run_id
        )
        
        return {
            "baseline_run_id": baseline_run_id,
            "outstanding_fails": len(outstanding_fails),
            "outstanding_warns": len(outstanding_warns),
            "can_finalize": len(outstanding_fails) == 0 and len(outstanding_warns) == 0,
            "fail_details": [
                {"type": f["finding_type"], "entity": f["entity_name"]} 
                for f in outstanding_fails[:10]
            ],
            "warn_details": [
                {"type": f["finding_type"], "entity": f["entity_name"]} 
                for f in outstanding_warns[:10]
            ],
        }


def main():
    """CLI entry point for finalize."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Finalize audit cycle")
    parser.add_argument("--db", default="output/audit_history.db")
    parser.add_argument("--excel", help="Excel file with annotations")
    parser.add_argument("--baseline", type=int, help="Baseline run ID (first if not specified)")
    parser.add_argument("--list", action="store_true", help="List finalized audits")
    parser.add_argument("--status", action="store_true", help="Check finalization status")
    parser.add_argument("--force", action="store_true", help="Force finalization despite issues")
    
    args = parser.parse_args()
    
    service = FinalizeService(db_path=args.db)
    
    if args.list:
        runs = service.get_finalized_runs()
        print(f"\nFinalized Audits: {len(runs)}")
        for run in runs:
            print(f"  Run #{run['id']}: {run['started_at']}")
        return 0
    
    if args.status:
        status = service.get_finalization_status(args.baseline)
        if "error" in status:
            print(f"\n❌ {status['error']}")
            return 1
        
        print(f"\n📋 Finalization Status for Run #{status['baseline_run_id']}")
        print("=" * 50)
        if status["can_finalize"]:
            print("✅ Ready to finalize - no outstanding issues")
        else:
            print(f"❌ FAIL findings: {status['outstanding_fails']}")
            print(f"⚠️  WARN findings: {status['outstanding_warns']}")
            print("\nUse --force to finalize anyway (not recommended)")
        return 0
    
    result = service.finalize(
        excel_path=args.excel,
        baseline_run_id=args.baseline,
        force=args.force
    )
    
    if "error" in result:
        print(f"\n{result['error']}")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ AUDIT FINALIZED!")
    print("=" * 60)
    print(f"   Run ID: #{result['baseline_run_id']}")
    print(f"   Annotations: {result['annotations_applied']}")
    if result.get("forced"):
        print(f"   ⚠️  Forced: Yes (bypassed checks)")
    print("")
    if result["actions"]:
        print("   Actions:")
        for action_type, count in result["actions"].items():
            icon = "✅" if action_type == "fixed" else "⚠️" if action_type == "still_failing" else "🆕"
            print(f"      {icon} {action_type}: {count}")
    
    if result.get("archive_path"):
        print(f"\n   📁 Archive: {result['archive_path']}")
    
    print("=" * 60)
    
    return 0


if __name__ == "__main__":
    exit(main())
