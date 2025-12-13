"""
AutoDBAudit CLI entry point.

Main entry point for the application CLI.
"""

import sys
import argparse
import logging
from pathlib import Path

from autodbaudit.application.audit_service import AuditService
from autodbaudit.application.audit_manager import AuditManager
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
        """,
    )

    # Audit commands
    parser.add_argument(
        "--audit", action="store_true", help="Run SQL Server security audit"
    )
    parser.add_argument(
        "--new", action="store_true", help="Create a new audit (use with --audit)"
    )
    parser.add_argument(
        "--id",
        type=int,
        dest="audit_id",
        help="Audit ID to continue (use with --audit, --generate-remediation, etc.)",
    )
    parser.add_argument(
        "--name",
        type=str,
        dest="audit_name",
        help="Name for new audit (use with --new)",
    )
    parser.add_argument("--list-audits", action="store_true", help="List all audits")
    parser.add_argument(
        "--config",
        type=str,
        default="audit_config.json",
        help="Audit configuration file (default: audit_config.json)",
    )
    parser.add_argument(
        "--targets",
        type=str,
        default="sql_targets.json",
        help="SQL targets configuration file (default: sql_targets.json)",
    )
    parser.add_argument(
        "--organization", type=str, help="Organization name for the audit report"
    )
    parser.add_argument(
        "--append-to",
        type=str,
        help="Append audit results to existing workbook (incremental)",
    )

    # Remediation commands
    parser.add_argument(
        "--generate-remediation",
        action="store_true",
        help="Generate individual remediation scripts",
    )
    parser.add_argument(
        "--aggressiveness",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Remediation intensity (1=Safe/Commented, 2=Revoke Privs, 3=Brutal/Disable)",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync progress: re-audit and log actions with timestamps",
    )
    parser.add_argument(
        "--finalize",
        action="store_true",
        help="Finalize audit: persist everything to SQLite",
    )
    parser.add_argument(
        "--baseline-run",
        type=int,
        help="Baseline run ID for --finalize (first if not specified)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force finalization despite outstanding issues (use with --finalize)",
    )
    parser.add_argument(
        "--finalize-status",
        action="store_true",
        help="Check finalization readiness without finalizing",
    )
    parser.add_argument(
        "--apply-remediation",
        action="store_true",
        help="Execute remediation scripts against SQL Server",
    )
    parser.add_argument(
        "--scripts", type=str, help="Path to scripts folder or single .sql file"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would execute without running"
    )
    parser.add_argument(
        "--rollback",
        action="store_true",
        help="Execute rollback scripts instead of remediation",
    )
    parser.add_argument(
        "--apply-exceptions",
        action="store_true",
        help="Read Notes/Reason from Excel and persist to SQLite",
    )
    parser.add_argument(
        "--excel",
        type=str,
        help="Excel file for --apply-exceptions (latest if not specified)",
    )
    parser.add_argument(
        "--status", action="store_true", help="Show audit status dashboard"
    )

    # Hotfix deployment commands
    parser.add_argument(
        "--deploy-hotfixes", action="store_true", help="Deploy SQL Server hotfixes"
    )
    parser.add_argument(
        "--retry-failed", action="store_true", help="Retry failed hotfix deployments"
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume hotfix deployment after cancellation",
    )

    # Utility commands
    parser.add_argument(
        "--check-drivers", action="store_true", help="Check available ODBC drivers"
    )
    parser.add_argument(
        "--setup-credentials",
        action="store_true",
        help="Encrypt credentials interactively",
    )
    parser.add_argument(
        "--validate-config", action="store_true", help="Validate configuration files"
    )

    # Logging
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--log-file", type=str, help="Write logs to file")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level, args.log_file)

    logger.info("AutoDBAudit starting...")

    try:
        # List audits command (before --audit so it takes precedence)
        if args.list_audits:
            manager = AuditManager(str(DEFAULT_OUTPUT_DIR))
            audits = manager.list_audits()
            if not audits:
                print("No audits found. Create one with: python main.py --audit --new")
                return 0

            print("\n📋 AUDITS")
            print("=" * 70)
            print(f"{'ID':<5} {'Name':<35} {'Status':<12} {'Runs':<6} Created")
            print("-" * 70)
            for a in audits:
                audit_id = a.get("id", 0)
                name = a.get("name", "")[:33]
                status = a.get("status", "")
                runs = len(a.get("runs", []))
                created = a.get("created", "")[:10]
                print(f"{audit_id:<5} {name:<35} {status:<12} {runs:<6} {created}")
            print()
            return 0

        if args.audit:
            return run_audit(args)

        elif args.generate_remediation:
            logger.info("Generating remediation scripts")
            manager = AuditManager(str(DEFAULT_OUTPUT_DIR))

            # Determine which audit to use
            if args.audit_id:
                audit_id = args.audit_id
                audit = manager.get_audit(audit_id)
                if not audit:
                    print(f"❌ Audit #{audit_id} not found")
                    return 1
            else:
                audit = manager.get_latest_audit()
                if not audit:
                    print("❌ No audits found. Run --audit first.")
                    return 1
                audit_id = audit["id"]

            # Create new remediation version
            version = manager.create_remediation_version(audit_id)
            scripts_folder = manager.get_remediation_scripts_folder(audit_id, version)

            # Use global DB for all audits
            db_path = DEFAULT_OUTPUT_DIR / "audit_history.db"

            print(
                f"\n📋 Generating remediation for Audit #{audit_id}: {audit.get('name', '')}"
            )
            print(f"   Version: v{version}")

            from autodbaudit.application.remediation_service import RemediationService

            # Get config snapshot to check for connecting users (SA lockout prevention)
            snapshot = manager.get_config_snapshot(audit_id)
            targets_config = snapshot.get("sql_targets", {})

            # Handle both list (legacy) and dict (new) config format
            if isinstance(targets_config, list):
                targets_list = targets_config
            else:
                targets_list = targets_config.get("targets", [])

            # Resolve credentials to get usernames for lockout checks
            # (Snapshot only stores paths, so we must load the user to know who connected)
            import json

            for target in targets_list:
                if target.get("auth") == "sql" and not target.get("username"):
                    cred_file = target.get("credential_file")
                    if cred_file:
                        try:
                            # Try relative to config dir
                            p = DEFAULT_CONFIG_DIR / cred_file
                            if not p.exists():
                                # Try relative to root
                                p = Path(cred_file)

                            if p.exists():
                                with open(p, "r", encoding="utf-8") as f:
                                    creds = json.load(f)
                                    # Handle both 'user' and 'username' keys
                                    target["username"] = creds.get("user") or creds.get(
                                        "username"
                                    )
                        except Exception as e:
                            logger.warning(
                                f"Failed to resolve credentials for {target.get('name')}: {e}"
                            )

            service = RemediationService(db_path=db_path, output_dir=scripts_folder)
            scripts = service.generate_scripts(
                sql_targets=targets_list, aggressiveness=args.aggressiveness
            )
            print(f"\n✅ Generated {len(scripts)} script(s) in {scripts_folder}")
            for s in scripts:
                print(f"   📄 {s}")
            return 0

        elif args.sync:
            logger.info("Syncing remediation progress")
            from autodbaudit.application.sync_service import SyncService

            # Initialize audit manager to get context
            manager = AuditManager(str(DEFAULT_OUTPUT_DIR))

            # Determine audit ID (prefer explicit, else latest running, else fail?)
            # Usually sync implies we are working on a running audit.
            audit_id = args.audit_id
            if not audit_id:
                latest = manager.get_latest_audit()
                if latest:
                    audit_id = latest["id"]
                    print(
                        f"📂 Syncing against latest Audit #{audit_id}: {latest.get('name', '')}"
                    )
                else:
                    print("⚠️  No audit found. Syncing in legacy mode (root output).")

            service = SyncService(db_path=DEFAULT_OUTPUT_DIR / "audit_history.db")
            result = service.sync(
                targets_file=args.targets, audit_manager=manager, audit_id=audit_id
            )

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

            # Get audit context
            manager = AuditManager(str(DEFAULT_OUTPUT_DIR))
            audit_id = args.audit_id
            if not audit_id:
                latest = manager.get_latest_audit()
                if latest:
                    audit_id = latest["id"]

            service = FinalizeService(
                db_path=DEFAULT_OUTPUT_DIR / "audit_history.db",
                output_dir=DEFAULT_OUTPUT_DIR
            )
            result = service.finalize(
                excel_path=args.excel,
                baseline_run_id=args.baseline_run,
                force=args.force,
                audit_manager=manager,
                audit_id=audit_id,
            )

            if "error" in result:
                # Multi-line errors for blocked finalization
                if result.get("blocked"):
                    print(f"\n{result['error']}")
                else:
                    print(f"\n❌ {result['error']}")
                return 1

            # Success output
            print("\n" + "=" * 60)
            print("✅ AUDIT FINALIZED!")
            print("=" * 60)
            print(f"   Run ID: #{result['baseline_run_id']}")
            print(f"   Annotations: {result['annotations_applied']}")
            if result.get("forced"):
                print("   ⚠️  Forced: Yes (bypassed safety checks)")
            print("")
            if result.get("actions"):
                print("   Actions:")
                for action_type, count in result["actions"].items():
                    icon = "✅" if action_type == "fixed" else "⚠️" if action_type == "still_failing" else "🆕"
                    print(f"      {icon} {action_type}: {count}")
            if result.get("archive_path"):
                print(f"\n   📁 Archive: {result['archive_path']}")
            print("=" * 60)
            return 0

        elif args.finalize_status:
            logger.info("Checking finalization status")
            from autodbaudit.application.finalize_service import FinalizeService

            service = FinalizeService(
                db_path=DEFAULT_OUTPUT_DIR / "audit_history.db"
            )
            status = service.get_finalization_status(args.baseline_run)

            if "error" in status:
                print(f"\n❌ {status['error']}")
                return 1

            print(f"\n📋 Finalization Status for Run #{status['baseline_run_id']}")
            print("=" * 50)
            
            if status["can_finalize"]:
                print("✅ Ready to finalize - no outstanding issues")
                print("\nRun: python main.py --finalize")
            else:
                print(f"❌ Outstanding FAIL findings: {status['outstanding_fails']}")
                for f in status.get("fail_details", []):
                    print(f"     • {f['type']}: {f['entity']}")
                print(f"⚠️  Outstanding WARN findings: {status['outstanding_warns']}")
                for f in status.get("warn_details", []):
                    print(f"     • {f['type']}: {f['entity']}")
                print("\nOptions:")
                print("  1. Fix issues and run --sync")
                print("  2. Add exceptions in Excel and run --apply-exceptions")
                print("  3. Use --finalize --force (not recommended)")
            return 0

        elif args.apply_exceptions:
            logger.info("Applying exceptions from Excel")
            from autodbaudit.application.exception_service import ExceptionService

            service = ExceptionService(
                db_path=DEFAULT_OUTPUT_DIR / "audit_history.db", excel_path=args.excel
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

            scripts_path = args.scripts or str(
                DEFAULT_OUTPUT_DIR / "remediation_scripts"
            )
            executor = ScriptExecutor(
                targets_file=args.targets,
                db_path=DEFAULT_OUTPUT_DIR / "audit_history.db",
            )

            path = Path(scripts_path)
            if path.is_dir():
                results = executor.execute_folder(
                    path, dry_run=args.dry_run, rollback=args.rollback
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
    Run the audit workflow with audit ID management.

    Args:
        args: Parsed command line arguments

    Returns:
        Exit code (0 = success)
    """
    logger.info("Running audit mode")

    # Initialize audit manager
    manager = AuditManager(str(DEFAULT_OUTPUT_DIR))

    # Determine audit ID
    if args.new:
        # Create new audit
        audit_id = manager.create_new_audit(
            name=args.audit_name or "", environment="", notes=""
        )
        print(f"\n🆕 Created new audit #{audit_id}")
    elif args.audit_id:
        # Continue existing audit
        audit_id = args.audit_id
        audit = manager.get_audit(audit_id)
        if not audit:
            print(f"❌ Audit #{audit_id} not found")
            print("   Use --list-audits to see available audits")
            return 1
        print(f"\n📂 Continuing audit #{audit_id}: {audit.get('name', '')}")
    else:
        # Check for existing audits to continue
        latest = manager.get_latest_audit()
        if latest and latest.get("status") == "in_progress":
            audit_id = latest["id"]
            print(f"\n📂 Continuing latest audit #{audit_id}: {latest.get('name', '')}")
            print("   (Use --new to start a fresh audit)")
        else:
            # Create new if no in-progress audit
            audit_id = manager.create_new_audit(
                name=args.audit_name or "", environment="", notes=""
            )
            print(f"\n🆕 Created new audit #{audit_id}")

    # Save config snapshot if first run for this audit
    config_snapshot = manager.get_config_snapshot(audit_id)
    if not config_snapshot.get("sql_targets"):
        try:
            # Load and snapshot the sql_targets config
            import json

            targets_path = DEFAULT_CONFIG_DIR / args.targets
            if targets_path.exists():
                with open(targets_path, "r", encoding="utf-8") as f:
                    sql_targets = json.load(f)
                manager.save_config_snapshot(audit_id, sql_targets)
                print(f"   📋 Saved config snapshot")
        except Exception as e:
            logger.warning("Could not save config snapshot: %s", e)

    # Create run within audit
    run_num = manager.create_run(audit_id)
    print(f"   Starting run #{run_num}")

    # Get paths for this run
    run_folder = manager._get_run_folder(audit_id, run_num)
    latest_excel_path = manager.get_latest_excel_path(audit_id)
    db_path = manager.get_global_db_path()

    # Create audit service with ROOT output dir (so audit_history.db is global)
    service = AuditService(
        config_dir=DEFAULT_CONFIG_DIR,
        output_dir=DEFAULT_OUTPUT_DIR,
    )

    # Run audit - writes Excel to root output dir, SQLite to audit_history.db
    report_path = service.run_audit(
        targets_file=args.targets, organization=args.organization
    )

    # Move Excel to run folder and copy to latest
    import shutil

    run_snapshot = run_folder / report_path.name
    shutil.copy(report_path, run_snapshot)
    shutil.copy(report_path, latest_excel_path)
    report_path.unlink()  # Remove from root output

    # Mark run complete
    manager.complete_run(audit_id, run_num, servers=0, findings=0)

    print(f"\n✅ Audit completed successfully!")
    print(f"📊 Run snapshot:  {report_path}")
    print(f"📊 Latest report: {latest_excel_path}")
    print(f"💾 Database:      {db_path}")

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
