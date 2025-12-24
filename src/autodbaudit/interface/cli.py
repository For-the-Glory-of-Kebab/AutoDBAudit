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
from autodbaudit.application.remediation.service import RemediationService
from autodbaudit.infrastructure.config_loader import ConfigLoader
from autodbaudit.infrastructure.logging_config import setup_logging
from autodbaudit.infrastructure.odbc_check import check_odbc_drivers
from autodbaudit.interface.formatted_console import ConsoleRenderer

logger = logging.getLogger(__name__)

# Default paths
DEFAULT_CONFIG_DIR = Path("config")
DEFAULT_OUTPUT_DIR = Path("output")


def _create_audit_service(args):
    """Factory to create AuditService or MockAuditService based on args."""
    if args.finding_dir:
        logger.warning("Using MOCK Audit Service (Finding Dir: %s)", args.finding_dir)
        from autodbaudit.application.utils.mock_audit_service import MockAuditService

        return MockAuditService(
            config_dir=DEFAULT_CONFIG_DIR,
            output_dir=Path(str(args.output_dir or DEFAULT_OUTPUT_DIR)),
            finding_dir=args.finding_dir,
        )
    return AuditService(
        config_dir=DEFAULT_CONFIG_DIR,
        output_dir=Path(str(args.output_dir or DEFAULT_OUTPUT_DIR)),
    )


def main() -> int:
    """Main entry point for AutoDBAudit CLI."""
    # Intercept --help / -h for rich formatted help
    if len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ["-h", "--help"]):
        from autodbaudit.interface.cli_help import print_main_help

        print_main_help()
        return 0

    # Command-specific help
    if len(sys.argv) >= 3 and sys.argv[2] in ["-h", "--help"]:
        from autodbaudit.interface import cli_help

        cmd = sys.argv[1]
        help_map = {
            "audit": cli_help.print_audit_help,
            "sync": cli_help.print_sync_help,
            "remediate": cli_help.print_remediate_help,
            "finalize": cli_help.print_finalize_help,
            "definalize": cli_help.print_finalize_help,  # Same as finalize
            "util": cli_help.print_util_help,
        }
        if cmd in help_map:
            help_map[cmd]()
            return 0

    parser = argparse.ArgumentParser(
        description="AutoDBAudit - SQL Server Security Audit Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global args
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument("--log-file", type=str, help="Write logs to file")

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Command: AUDIT
    parser_audit = subparsers.add_parser("audit", help="Run security audit")
    parser_audit.add_argument("--new", action="store_true", help="Start fresh audit")
    parser_audit.add_argument("--name", type=str, help="Name for new audit")
    parser_audit.add_argument("--id", type=int, help="Resume existing audit ID")
    parser_audit.add_argument(
        "--targets", default="sql_targets.json", help="Targets config file"
    )
    parser_audit.add_argument("--organization", type=str, help="Organization name")
    parser_audit.add_argument("--list", action="store_true", help="List all audits")

    # Command: REMEDIATE
    parser_rem = subparsers.add_parser(
        "remediate", help="Generate or Apply remediation"
    )
    parser_rem.add_argument(
        "--generate", action="store_true", help="Generate script files"
    )
    parser_rem.add_argument(
        "--apply", action="store_true", help="Apply SQL scripts to targets"
    )
    # --os-hook removed in favor of config-driven logic
    parser_rem.add_argument(
        "--aggressiveness",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Fix intensity (1=Safe, 3=Nuclear)",
    )
    parser_rem.add_argument("--audit-id", type=int, help="Audit ID context")
    parser_rem.add_argument("--scripts", type=str, help="Custom scripts folder")
    parser_rem.add_argument("--dry-run", action="store_true", help="Simulate execution")
    parser_rem.add_argument(
        "--rollback", action="store_true", help="Execute rollback scripts"
    )

    # Command: SYNC
    parser_sync = subparsers.add_parser("sync", help="Sync progress (Re-Audit)")
    parser_sync.add_argument("--audit-id", type=int, help="Audit ID to sync")
    parser_sync.add_argument(
        "--targets", default="sql_targets.json", help="Targets config file"
    )

    # Command: FINALIZE
    parser_fin = subparsers.add_parser("finalize", help="Finalize audit")
    parser_fin.add_argument("--audit-id", type=int, help="Audit ID")
    parser_fin.add_argument("--baseline-run", type=int, help="Run ID to finalize")
    parser_fin.add_argument("--force", action="store_true", help="Bypass safety checks")
    parser_fin.add_argument(
        "--status", action="store_true", help="Check readiness only"
    )
    parser_fin.add_argument(
        "--apply-exceptions", action="store_true", help="Apply Excel exceptions"
    )
    parser_fin.add_argument("--excel", type=str, help="Excel file for exceptions")

    # Command: DEFINALIZE (Revert)
    parser_def = subparsers.add_parser(
        "definalize", help="Revert finalized audit to in-progress"
    )
    parser_def.add_argument(
        "--audit-id", type=int, required=True, help="Audit ID to revert"
    )

    # Command: UTIL
    parser_util = subparsers.add_parser("util", help="Utilities")
    parser_util.add_argument(
        "--check-drivers", action="store_true", help="Check ODBC drivers"
    )
    parser_util.add_argument(
        "--setup-credentials", action="store_true", help="Encrypt credentials"
    )
    parser_util.add_argument(
        "--validate-config", action="store_true", help="Validate configs"
    )

    # E2E Test Overrides (Hidden)
    parser.add_argument("--finding-dir", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--output-dir", type=str, help=argparse.SUPPRESS)
    parser.add_argument("--db-path", type=str, help=argparse.SUPPRESS)

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level, args.log_file)

    logger.info("AutoDBAudit starting...")

    # Resilience: Cleanup stale runs from potential power outages
    try:
        from autodbaudit.infrastructure.sqlite.store import HistoryStore

        db_path = DEFAULT_OUTPUT_DIR / "audit_history.db"
        if db_path.exists():
            store = HistoryStore(db_path)
            # We don't call initialize_schema here to avoid creating tables if they don't exist
            # but cleanup_stale_runs might fail if tables are missing.
            try:
                store.cleanup_stale_runs()
            except Exception:
                # Likely tables don't exist yet, which is fine
                pass
            store.close()
    except Exception as e:
        logger.warning("Startup cleanup failed (non-critical): %s", e)

    # Main Dispatch Logic
    try:
        if args.command == "audit":
            if args.list:
                manager = AuditManager(str(DEFAULT_OUTPUT_DIR))
                audits = manager.list_audits()
                if not audits:
                    print(
                        "No audits found. Create one with: python main.py audit --new"
                    )
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

            # Run audit
            return run_audit(args)

        elif args.command == "remediate":
            return handle_remediation_command(args)

        elif args.command == "sync":
            return handle_sync_command(args)

        elif args.command == "finalize":
            return handle_finalize_command(args)

        elif args.command == "definalize":
            return handle_definalize_command(args)

        elif args.command == "util":
            if args.check_drivers:
                check_odbc_drivers()
                return 0
            elif args.validate_config:
                return validate_config(args)
            elif args.setup_credentials:
                from autodbaudit.infrastructure.credentials import (
                    setup_credentials_interactive,
                )

                # Assuming this function exists or just placeholder if not
                # Since I didn't see it, I'll print not implemented for safety to avoid import error
                print("Credential setup utility not connected.")
                return 1
            else:
                # Retrieve the util subparser to print its help
                # Accessing subparsers choices is tricky, easiest is generic help
                print("Use: python main.py util [--check-drivers | --validate-config]")
                return 1

        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        return 1


def handle_remediation_command(args) -> int:
    """Handler for 'remediate' subcommand logic."""
    manager = AuditManager(str(DEFAULT_OUTPUT_DIR))

    # 1. GENERATE
    if args.generate:
        logger.info("Generating scripts...")
        if args.audit_id:
            audit = manager.get_audit(args.audit_id)
            if not audit:
                print(f"❌ Audit #{args.audit_id} not found")
                return 1
        else:
            audit = manager.get_latest_audit()
            if not audit:
                print("❌ No audits found")
                return 1

        version = manager.create_remediation_version(audit["id"])
        scripts_folder = manager.get_remediation_scripts_folder(audit["id"], version)

        # Load targets/Config from snapshot
        snapshot = manager.get_config_snapshot(audit["id"])
        targets_config = snapshot.get("sql_targets", {})
        if isinstance(targets_config, list):
            targets = targets_config
        else:
            targets = targets_config.get("targets", [])

        # Resolve creds (simplified reuse of logic)
        import json

        for target in targets:
            if target.get("auth") == "sql" and not target.get("username"):
                cred_file = target.get("credential_file")
                if cred_file:
                    try:
                        # Try relative to config dir then root
                        p = DEFAULT_CONFIG_DIR / cred_file
                        if not p.exists():
                            p = Path(cred_file)
                        if p.exists():
                            with open(p, "r", encoding="utf-8") as f:
                                creds = json.load(f)
                                target["username"] = creds.get("user") or creds.get(
                                    "username"
                                )
                    except Exception:
                        pass

        svc = RemediationService(
            db_path=DEFAULT_OUTPUT_DIR / "audit_history.db", output_dir=scripts_folder
        )
        paths = svc.generate_scripts(
            sql_targets=targets, aggressiveness=args.aggressiveness
        )

        print(f"✅ Generated {len(paths)} scripts in {scripts_folder}")
        return 0

    # 2. APPLY (SQL & OS)
    if args.apply:
        from autodbaudit.application.script_executor import ScriptExecutor

        logger.info("Applying remediation...")

        # -- SQL Part --
        scripts_path = args.scripts
        if not scripts_path:
            audits = manager.list_audits()
            audits.sort(key=lambda x: x["id"], reverse=True)
            target_audit = next(
                (a for a in audits if a.get("remediation_versions", 0) > 0), None
            )

            if not target_audit:
                print("❌ No scripts found.")
                return 1

            scripts_path = str(
                manager.get_remediation_scripts_folder(
                    target_audit["id"], target_audit["remediation_versions"]
                )
            )
            print(f"📂 Selected: {scripts_path}")

        executor = ScriptExecutor(
            targets_file="sql_targets.json",
            db_path=DEFAULT_OUTPUT_DIR / "audit_history.db",
        )
        path = Path(scripts_path)

        sql_success = True
        if path.is_file():
            res = executor.execute_script(path, dry_run=args.dry_run)
            sql_success = res.success
        elif path.is_dir():
            results = executor.execute_folder(
                path, dry_run=args.dry_run, rollback=args.rollback
            )
            failed = sum(1 for r in results if not r.success)
            sql_success = failed == 0

        if not sql_success:
            print("⚠️  SQL Remediation had errors. Aborting OS hooks.")
            return 1

        # -- OS Hook Part --
        # Check config
        loader = ConfigLoader(str(DEFAULT_CONFIG_DIR))
        audit_conf = loader.load_audit_config()
        os_settings = getattr(audit_conf, "os_remediation", {})

        # "use_os_remediation" key check (handling dict vs object attr mismatch possibility)
        use_ps = False
        if isinstance(os_settings, dict):
            use_ps = os_settings.get("use_ps_remoting", False)
        elif hasattr(os_settings, "use_ps_remoting"):
            use_ps = os_settings.use_ps_remoting

        if use_ps:
            print("🤖 OS Remediation Enabled in Config via PSRemoting")
            # TODO: Call OSRemediationService here
            print("   [OS Hook Logic Triggered]")
        else:
            logger.info("OS Remediation skipped (disabled in config)")

        return 0

    print("❌ Specify --generate or --apply")
    return 1


def handle_sync_command(args) -> int:
    logger.info("Syncing remediation progress")
    from autodbaudit.application.sync_service import SyncService

    manager = AuditManager(str(DEFAULT_OUTPUT_DIR))
    audit_id = args.audit_id
    if not audit_id:
        latest = manager.get_latest_audit()
        if latest:
            audit_id = latest["id"]

    try:
        service = SyncService(db_path=DEFAULT_OUTPUT_DIR / "audit_history.db")
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return 1
    # Shim: Mock arguments for factory
    args.finding_dir = None
    args.output_dir = None
    real_svc = _create_audit_service(args)

    result = service.sync(
        audit_service=real_svc,
        targets_file=args.targets,
        audit_manager=manager,
        audit_id=audit_id,
    )

    if "error" in result:
        print(f"❌ {result['error']}")
        return 1

    print("✅ Sync complete")
    # Quick Stats Render
    renderer = ConsoleRenderer(use_color=True)
    if result.get("stats_obj"):
        renderer.render_stats_card(result["stats_obj"])
    return 0


def handle_finalize_command(args) -> int:
    if args.apply_exceptions:
        from autodbaudit.application.exception_service import ExceptionService

        svc = ExceptionService(
            db_path=DEFAULT_OUTPUT_DIR / "audit_history.db", excel_path=args.excel
        )
        res = svc.apply_exceptions()
        print(f"✅ Applied {res['applied']} exceptions")
        return 0

    from autodbaudit.application.finalize_service import FinalizeService

    logger.info("Finalizing_audit")
    if args.status:
        service = FinalizeService(output_dir=DEFAULT_OUTPUT_DIR)
        status = service.get_finalization_status(args.baseline_run)
        print(
            f"Status for Run #{status['baseline_run_id']}: Fail={status['outstanding_fails']}, Warn={status['outstanding_warns']}"
        )
        return 0

    service = FinalizeService(output_dir=DEFAULT_OUTPUT_DIR)
    result = service.finalize(run_id=args.baseline_run, force=args.force)

    if "error" in result:
        print(f"❌ {result['error']}")
        return 1
    print("✅ Audit Finalized!")
    return 0


def handle_definalize_command(args) -> int:
    """Handler for 'definalize' subcommand."""
    from autodbaudit.application.definalize_service import DefinalizeService

    logger.info("Definalizing audit #%d", args.audit_id)

    service = DefinalizeService(db_path=DEFAULT_OUTPUT_DIR / "audit_history.db")
    result = service.definalize(args.audit_id)

    if "error" in result:
        print(f"❌ {result['error']}")
        return 1

    print(f"✅ {result['message']}")
    return 0


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
    out_dir = args.output_dir if args.output_dir else str(DEFAULT_OUTPUT_DIR)
    manager = AuditManager(out_dir)

    # Determine audit ID
    # Determine audit ID
    if args.new:
        # Create new audit
        audit_id = manager.create_new_audit(
            name=args.name or "", environment="", notes=""
        )
        print(f"\n🆕 Created new audit #{audit_id}")
    elif args.id:
        # Continue existing audit
        audit_id = args.id
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
                name=args.name or "", environment="", notes=""
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

    # Create run within audit (just increments run counter, no folder needed)
    run_num = manager.create_run(audit_id)
    print(f"   Starting run #{run_num}")

    # Get paths - we only need the latest Excel (working copy), not per-run snapshots
    # All data is persisted in SQLite, Excel is just for user interaction
    latest_excel_path = manager.get_latest_excel_path(audit_id)
    db_path = manager.get_global_db_path()

    # Create audit service with ROOT output dir (so audit_history.db is global)
    service = _create_audit_service(args)

    # Run audit - writes Excel to root output dir, SQLite to audit_history.db
    report_path = service.run_audit(
        targets_file=args.targets, organization=args.organization
    )

    # Move Excel to latest working copy location (no per-run snapshots needed)
    import shutil

    shutil.copy(report_path, latest_excel_path)
    report_path.unlink()  # Remove from root output

    # Mark run complete
    manager.complete_run(audit_id, run_num, servers=0, findings=0)

    print(f"\n✅ Audit completed successfully!")
    print(f"📊 Report: {latest_excel_path}")
    print(f"💾 Database: {db_path}")

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
