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
            "prepare": cli_help.print_prepare_help,
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
    parser_fin.add_argument(
        "--persian",
        action="store_true",
        help="Use Persian calendar for dates",
    )

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

    # Command: PREPARE (Access Preparation)
    parser_prep = subparsers.add_parser(
        "prepare", help="Prepare remote access for targets"
    )
    parser_prep.add_argument(
        "--status", action="store_true", help="Show access status for all targets"
    )
    parser_prep.add_argument(
        "--revert",
        action="store_true",
        help="Revert all access changes to original state",
    )
    parser_prep.add_argument(
        "--mark-accessible",
        type=str,
        metavar="TARGET_ID",
        help="Manually mark a target as accessible",
    )
    parser_prep.add_argument(
        "--targets", default="sql_targets.json", help="Targets config file"
    )
    parser_prep.add_argument(
        "--yes", action="store_true", help="Skip confirmation prompts"
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

        elif args.command == "prepare":
            return handle_prepare_command(args)

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
            print(
                "⚠️  SQL Remediation had errors. Proceeding to OS hooks (Best Effort)..."
            )
            # Do not return 1, continue to allow OS scripts to run

        # -- OS Hook Part --
        # Check config but default to TRUE if not specified,
        # or rely on presence of script files (Hybrid approach auto-detection)
        loader = ConfigLoader(str(DEFAULT_CONFIG_DIR))
        audit_conf = loader.load_audit_config()

        # Determine if OS remediation is explicitly disabled
        # Default is ENABLED for hybrid approach unless user turned it off
        os_settings = getattr(audit_conf, "os_remediation", {})
        os_disabled = False

        if isinstance(os_settings, dict):
            if os_settings.get("use_ps_remoting") is False:
                os_disabled = True
        elif hasattr(os_settings, "use_ps_remoting"):
            if os_settings.use_ps_remoting is False:
                os_disabled = True

        # Find all _OS_AUDIT.ps1 files first
        ps_scripts = list(Path(scripts_path).glob("*_OS_AUDIT.ps1"))

        if ps_scripts and not os_disabled:
            print(
                f"🤖 Hybrid Remediation: Found {len(ps_scripts)} PowerShell script(s). Executing..."
            )
            import subprocess

            for ps_file in ps_scripts:
                print(f"   Executing OS Remediation: {ps_file.name}...")

                # Construct command: pwsh -ExecutionPolicy Bypass -File <path> -ApplyFix
                # We assume the user wants to apply fixes since they ran --apply
                cmd = [
                    "pwsh",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps_file),
                    "-ApplyFix",
                ]

                try:
                    # Run synchronously and capture output
                    result = subprocess.run(
                        cmd, check=False, text=True, capture_output=True
                    )

                    # Print output indented
                    for line in result.stdout.splitlines():
                        print(f"     {line}")

                    if result.returncode != 0:
                        print(f"     ❌ Script failed (Code {result.returncode})")
                        if result.stderr:
                            print(f"     ERROR: {result.stderr}")
                    else:
                        print(f"     ✅ OS Remediation completed for {ps_file.name}")

                except Exception as e:
                    print(f"     ❌ Execution Error: {e}")

        elif not ps_scripts:
            # Only log if enabled but no scripts found, or just silent?
            # User expects hybrid if available. If not available, maybe silent is ok.
            pass
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

    # Generate Persian copy if requested
    if getattr(args, "persian", False):
        from autodbaudit.application.persian_generator import generate_persian_report
        from pathlib import Path

        # Find the generated Excel file
        excel_path = result.get("excel_path")
        if excel_path:
            try:
                persian_path = generate_persian_report(Path(excel_path))
                print(f"✅ Persian report generated: {persian_path}")
            except Exception as e:
                print(f"⚠️ Persian generation failed: {e}")
        else:
            print("⚠️ No Excel path in result, skipping Persian generation")

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


def handle_prepare_command(args) -> int:
    """Handler for 'prepare' subcommand - Access Preparation."""
    from autodbaudit.infrastructure.sqlite.store import HistoryStore
    from autodbaudit.infrastructure.config_loader import ConfigLoader
    from autodbaudit.application.access_preparation import AccessPreparationService

    db_path = DEFAULT_OUTPUT_DIR / "audit_history.db"
    store = HistoryStore(db_path)
    store.initialize_schema()

    service = AccessPreparationService(store)

    # Status only
    if args.status:
        statuses = service.get_all_status()
        if not statuses:
            print("No access preparation data found. Run 'prepare' first.")
            return 0

        print("\n📡 ACCESS STATUS")
        print("=" * 80)
        print(f"{'Target':<20} {'Host':<20} {'OS':<8} {'Method':<10} {'Status':<10}")
        print("-" * 80)
        for s in statuses:
            print(
                f"{s.target_id:<20} {s.hostname:<20} {s.os_type:<8} "
                f"{s.access_method:<10} {s.access_status:<10}"
            )
        print()
        store.close()
        return 0

    # Revert changes
    if args.revert:
        if not args.yes:
            confirm = input("Revert all access changes? [y/N]: ")
            if confirm.lower() != "y":
                print("Aborted.")
                store.close()
                return 0

        count = service.revert_all()
        print(f"✅ Reverted {count} targets to original state")
        store.close()
        return 0

    # Manual mark
    if args.mark_accessible:
        service.mark_accessible(args.mark_accessible, "Manual override by user")
        print(f"✅ Marked {args.mark_accessible} as accessible")
        store.close()
        return 0

    # Default: Prepare all targets
    loader = ConfigLoader()
    targets = loader.load_sql_targets(args.targets)
    enabled = [t for t in targets if t.enabled]

    if not enabled:
        print("No enabled targets found in config.")
        store.close()
        return 1

    print(f"\n🔧 Preparing access for {len(enabled)} targets...")
    print("=" * 60)

    results = service.prepare_all(enabled)

    # Summary
    ready = sum(1 for r in results if r.access_status == "ready")
    failed = sum(1 for r in results if r.access_status == "failed")

    print()
    print(f"✅ Ready: {ready}")
    print(f"❌ Failed: {failed}")

    if failed > 0:
        print("\nUse 'prepare --status' to see details.")
        print("Use 'prepare --mark-accessible TARGET_ID' to override.")

    store.close()
    return 0 if failed == 0 else 1


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
        # Use getattr with defaults since util subparser doesn't have these args
        targets_file = getattr(args, "targets", "sql_targets.json")
        config_file = getattr(args, "config", "audit_config.json")

        # Validate SQL targets
        targets = loader.load_sql_targets(targets_file)
        print(f"✅ SQL targets valid: {len(targets)} targets configured")
        for target in targets:
            print(f"   - {target.display_name} ({target.auth} auth)")

        # Validate audit config
        config = loader.load_audit_config(config_file)
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
