"""
AutoDBAudit CLI entry point.

Main entry point for the application CLI.
"""

import sys
import argparse
import logging
from pathlib import Path

from autodbaudit.application.audit_service import AuditService
from autodbaudit.infrastructure.config_loader import ConfigLoader
from autodbaudit.infrastructure.logging_config import setup_logging
from autodbaudit.infrastructure.odbc_check import check_odbc_drivers

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CONFIG_DIR = Path("config")
DEFAULT_OUTPUT_DIR = Path("output")


def main() -> int:
    """Main entry point for AutoDBAudit CLI."""
    parser = argparse.ArgumentParser(
        description="AutoDBAudit - SQL Server Security Audit Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --audit                         Run audit with default config
  python main.py --audit --targets custom.json   Use custom targets file
  python main.py --check-drivers                 List available ODBC drivers
  python main.py --validate-config               Validate configuration files
        """
    )
    
    # Audit commands
    parser.add_argument("--audit", action="store_true",
                       help="Run SQL Server security audit")
    parser.add_argument("--config", type=str, default="audit_config.json",
                       help="Audit configuration file (default: audit_config.json)")
    parser.add_argument("--targets", type=str, default="sql_targets.json",
                       help="SQL targets configuration file (default: sql_targets.json)")
    parser.add_argument("--organization", type=str,
                       help="Organization name for the audit report")
    parser.add_argument("--append-to", type=str,
                       help="Append audit results to existing workbook (incremental)")
    
    # Remediation commands
    parser.add_argument("--generate-remediation", action="store_true",
                       help="Generate individual remediation scripts")
    parser.add_argument("--sync", action="store_true",
                       help="Sync progress: re-audit and log actions with timestamps")
    parser.add_argument("--finalize", action="store_true",
                       help="Finalize audit: persist everything to SQLite")
    parser.add_argument("--baseline-run", type=int,
                       help="Baseline run ID for --finalize (first if not specified)")
    parser.add_argument("--apply-remediation", action="store_true",
                       help="Execute remediation scripts against SQL Server")
    parser.add_argument("--scripts", type=str,
                       help="Path to scripts folder or single .sql file")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would execute without running")
    parser.add_argument("--rollback", action="store_true",
                       help="Execute rollback scripts instead of remediation")
    parser.add_argument("--apply-exceptions", action="store_true",
                       help="Read Notes/Reason from Excel and persist to SQLite")
    parser.add_argument("--excel", type=str,
                       help="Excel file for --apply-exceptions (latest if not specified)")
    parser.add_argument("--status", action="store_true",
                       help="Show audit status dashboard")
    
    # Hotfix deployment commands
    parser.add_argument("--deploy-hotfixes", action="store_true",
                       help="Deploy SQL Server hotfixes")
    parser.add_argument("--retry-failed", action="store_true",
                       help="Retry failed hotfix deployments")
    parser.add_argument("--resume", action="store_true",
                       help="Resume hotfix deployment after cancellation")
    
    # Utility commands
    parser.add_argument("--check-drivers", action="store_true",
                       help="Check available ODBC drivers")
    parser.add_argument("--setup-credentials", action="store_true",
                       help="Encrypt credentials interactively")
    parser.add_argument("--validate-config", action="store_true",
                       help="Validate configuration files")
    
    # Logging
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    parser.add_argument("--log-file", type=str,
                       help="Write logs to file")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level, args.log_file)
    
    logger.info("AutoDBAudit starting...")
    
    try:
        if args.audit:
            return run_audit(args)
        
        elif args.generate_remediation:
            logger.info("Generating remediation scripts")
            from autodbaudit.application.remediation_service import RemediationService
            service = RemediationService(
                db_path=DEFAULT_OUTPUT_DIR / "audit_history.db",
                output_dir=DEFAULT_OUTPUT_DIR / "remediation_scripts"
            )
            scripts = service.generate_scripts()
            print(f"\n✅ Generated {len(scripts)} remediation script(s):")
            for s in scripts:
                print(f"   📄 {s}")
            return 0
        
        elif args.sync:
            logger.info("Syncing remediation progress")
            from autodbaudit.application.sync_service import SyncService
            service = SyncService(db_path=DEFAULT_OUTPUT_DIR / "audit_history.db")
            result = service.sync(targets_file=args.targets)
            
            if "error" in result:
                print(f"\n❌ {result['error']}")
                return 1
            
            print(f"\n✅ Sync complete!")
            print(f"   Baseline: Run #{result['initial_run_id']}")
            print(f"   Current:  Run #{result['current_run_id']}")
            print("")
            print(f"   ✅ Fixed:         {result['fixed']}")
            print(f"   ⚠️  Still Failing: {result['still_failing']}")
            print(f"   🔴 Regression:    {result['regression']}")
            print(f"   🆕 New:           {result['new']}")
            return 0
        
        elif args.finalize:
            logger.info("Finalizing audit")
            from autodbaudit.application.finalize_service import FinalizeService
            service = FinalizeService(db_path=DEFAULT_OUTPUT_DIR / "audit_history.db")
            result = service.finalize(
                excel_path=args.excel,
                baseline_run_id=args.baseline_run
            )
            
            if "error" in result:
                print(f"\n❌ {result['error']}")
                return 1
            
            print("\n✅ Audit Finalized!")
            print(f"   Run ID: #{result['baseline_run_id']}")
            print(f"   Annotations: {result['annotations_applied']}")
            if result.get("actions"):
                print("")
                print("   Actions:")
                for action_type, count in result["actions"].items():
                    print(f"      {action_type}: {count}")
            return 0
        
        elif args.apply_exceptions:
            logger.info("Applying exceptions from Excel")
            from autodbaudit.application.exception_service import ExceptionService
            service = ExceptionService(
                db_path=DEFAULT_OUTPUT_DIR / "audit_history.db",
                excel_path=args.excel
            )
            result = service.apply_exceptions()
            
            if "error" in result:
                print(f"\n❌ {result['error']}")
                return 1
            
            print(f"\n✅ Applied {result['applied']} annotation(s)")
            if result.get("errors"):
                print(f"   ⚠️  {result['errors']} error(s)")
            return 0
        
        elif args.status:
            from autodbaudit.application.status_service import StatusService
            try:
                service = StatusService(db_path=DEFAULT_OUTPUT_DIR / "audit_history.db")
                service.print_status()
                return 0
            except FileNotFoundError as e:
                print(f"\n❌ {e}")
                return 1
        
        elif args.apply_remediation:
            from autodbaudit.application.script_executor import ScriptExecutor
            
            scripts_path = args.scripts or str(DEFAULT_OUTPUT_DIR / "remediation_scripts")
            executor = ScriptExecutor(
                targets_file=args.targets,
                db_path=DEFAULT_OUTPUT_DIR / "audit_history.db"
            )
            
            path = Path(scripts_path)
            if path.is_dir():
                results = executor.execute_folder(
                    path, 
                    dry_run=args.dry_run,
                    rollback=args.rollback
                )
                failed = sum(1 for r in results if not r.success)
                return 1 if failed > 0 else 0
            elif path.is_file() and path.suffix == ".sql":
                result = executor.execute_script(path, dry_run=args.dry_run)
                return 0 if result.success else 1
            else:
                print(f"❌ Invalid path: {scripts_path}")
                print("   Specify --scripts as folder or .sql file")
                return 1
        
        elif args.deploy_hotfixes:
            logger.info("Deploying hotfixes")
            print("Hotfix deployment - implementation pending (Phase 5)")
            return 0
        
        elif args.check_drivers:
            check_odbc_drivers()
            return 0
        
        elif args.validate_config:
            return validate_config(args)
        
        else:
            parser.print_help()
            return 1
        
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        return 1


def run_audit(args: argparse.Namespace) -> int:
    """
    Run the audit workflow.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 = success)
    """
    logger.info("Running audit mode")
    
    # Ensure output directory exists
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create audit service (no HistoryStore for now - direct Excel generation)
    service = AuditService(
        config_dir=DEFAULT_CONFIG_DIR,
        output_dir=DEFAULT_OUTPUT_DIR
    )
    
    # Run audit
    report_path = service.run_audit(
        targets_file=args.targets,
        organization=args.organization
    )
    
    print(f"\n✅ Audit completed successfully!")
    print(f"📊 Security audit report: {report_path}")
    
    return 0



def validate_config(args: argparse.Namespace) -> int:
    """
    Validate configuration files.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 = valid)
    """
    logger.info("Validating configuration files")
    
    loader = ConfigLoader(str(DEFAULT_CONFIG_DIR))
    
    try:
        # Validate SQL targets
        targets = loader.load_sql_targets(args.targets)
        print(f"✅ SQL targets valid: {len(targets)} targets configured")
        for target in targets:
            print(f"   - {target.display_name} ({target.auth} auth)")
        
        # Validate audit config
        config = loader.load_audit_config(args.config)
        print(f"✅ Audit config valid: {config.organization} ({config.audit_year})")
        
        return 0
        
    except FileNotFoundError as e:
        print(f"❌ Configuration file not found: {e}")
        return 1
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
