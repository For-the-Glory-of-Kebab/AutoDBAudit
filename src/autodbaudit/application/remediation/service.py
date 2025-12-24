"""
Modular Remediation Service.
Orchestrates generation of scripts using specialized handlers.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from pathlib import Path
from datetime import datetime
import sqlite3

from autodbaudit.application.remediation.handlers.base import RemediationContext
from autodbaudit.application.remediation.handlers.configuration import (
    ConfigurationHandler,
)
from autodbaudit.application.remediation.handlers.access_control import (
    AccessControlHandler,
)
from autodbaudit.application.remediation.handlers.database import DatabaseHandler
from autodbaudit.application.remediation.handlers.infrastructure import (
    InfrastructureHandler,
)

if TYPE_CHECKING:
    from autodbaudit.application.remediation.handlers.base import RemediationAction

logger = logging.getLogger(__name__)


class RemediationService:
    """
    Service for generating smart T-SQL remediation scripts.
    Delegates finding resolution to specialized Handlers.
    """

    def __init__(
        self,
        db_path: str | Path = "output/audit_history.db",
        output_dir: str | Path = "output/remediation_scripts",
    ):
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # We need to track secrets globally? No, context will track them per instance.
        logger.info("Modular RemediationService initialized")

    def generate_scripts(
        self,
        audit_run_id: int | None = None,
        sql_targets: list[dict] | None = None,
        aggressiveness: int = 1,
    ) -> list[Path]:
        """
        Generate remediation scripts for all findings.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get latest run if not specified
        if audit_run_id is None:
            row = conn.execute(
                "SELECT id FROM audit_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                logger.error("No audit runs found")
                conn.close()
                return []
            audit_run_id = row["id"]

        # Get findings
        findings = conn.execute(
            """
            SELECT f.*, i.instance_name, i.id as instance_db_id, s.hostname as server_name
            FROM findings f
            JOIN instances i ON f.instance_id = i.id
            JOIN servers s ON i.server_id = s.id
            WHERE f.audit_run_id = ?
            AND f.status IN ('FAIL', 'WARN')
            ORDER BY s.hostname, i.instance_name, f.finding_type
        """,
            (audit_run_id,),
        ).fetchall()
        findings = [dict(f) for f in findings]  # Convert to dicts

        # CRITICAL: Also fetch SA accounts from logins table (they may not be in findings)
        sa_accounts = conn.execute(
            """
            SELECT l.login_name as entity_name, l.is_disabled,
                   i.instance_name, i.id as instance_db_id, s.hostname as server_name
            FROM logins l
            JOIN instances i ON l.instance_id = i.id
            JOIN servers s ON i.server_id = s.id
            WHERE l.audit_run_id = ?
            AND l.is_sa_account = 1
            AND l.is_disabled = 0
        """,
            (audit_run_id,),
        ).fetchall()

        for sa in sa_accounts:
            # Inject synthetic SA finding
            findings.append(
                {
                    "finding_type": "sa_account",
                    "entity_name": sa["entity_name"],
                    "status": "FAIL",
                    "server_name": sa["server_name"],
                    "instance_name": sa["instance_name"],
                    "instance_db_id": sa["instance_db_id"],
                    "finding_description": "SA account is enabled",
                    "recommendation": "Disable SA account",
                }
            )
            logger.info(
                "Injected SA account finding for %s\\%s",
                sa["server_name"],
                sa["instance_name"],
            )

        conn.close()

        if not findings:
            logger.info("No findings requiring remediation")
            return []

        # Map (server, instance) -> port
        # Because instances table doesn't store port, we must look it up from config
        instance_port_map = {}
        conn_user_map = {}

        if sql_targets:
            for t in sql_targets:
                srv = t.get("server", "").lower()
                inst = (
                    t.get("instance") or "DEFAULT"
                ).upper()  # Normalize None to DEFAULT
                # Actually, instance name in DB might be "MSSQLSERVER" for default
                # But assume sql_targets matches what we found or close enough
                # If target has "instance" field use it, else try to infer

                port = t.get("port") or 1433
                conn_user = t.get("username", "")

                # We need to match what's in the DB.
                # DB has 'instance_name' which comes from actual connection (e.g. MSSQLSERVER)
                # target config has 'instance' (optional) or we rely on port.

                # Let's map (srv, inst) -> port if feasible, else default 1433.
                # For remediation generation, best effort is okay.

                # Using just server+port from config for user map
                conn_user_map[(srv, port)] = conn_user

                # Also store for port lookup if we can match server
                # But we don't know the DB instance name easily for the key without more logic
                # So let's iterate findings and best-match.

        # Group by instance
        by_instance: dict[tuple, list] = {}
        for f in findings:
            inst_id = f["instance_db_id"]
            server_name = f["server_name"]
            instance_name = f["instance_name"]

            # Try to find port from targets
            port = 1433
            if sql_targets:
                for t in sql_targets:
                    # Simple case-insensitive hostname match
                    if t.get("server", "").lower() == server_name.lower():
                        # If finding instance is MSSQLSERVER and target instance is None/Default -> match
                        # If finding instance matches target instance -> match
                        tgt_inst = t.get("instance")
                        if tgt_inst and tgt_inst.lower() == instance_name.lower():
                            port = t.get("port") or 1433
                            break
                        if not tgt_inst and instance_name == "MSSQLSERVER":
                            port = t.get("port") or 1433
                            break

            key = (server_name, instance_name, port, inst_id)
            if key not in by_instance:
                by_instance[key] = []
            by_instance[key].append(dict(f))

        generated = []
        for (server, instance, port, inst_id), instance_findings in by_instance.items():
            conn_user = conn_user_map.get((server.lower(), port))

            paths = self._generate_instance_scripts(
                server,
                instance,
                inst_id,
                port,
                instance_findings,
                conn_user,
                aggressiveness,
            )
            generated.extend(paths)

        logger.info("Generated %d script files", len(generated))
        return generated

    def _generate_instance_scripts(
        self,
        server: str,
        instance: str,
        inst_id: int,
        port: int,
        findings: list[dict],
        conn_user: str | None,
        aggressiveness: int,
    ) -> list[Path]:
        """Generate scripts for a single instance using Handlers."""

        # Initialize Context
        context = RemediationContext(
            server_name=server,
            instance_name=instance,
            inst_id=inst_id,
            port=port,
            conn_user=conn_user,
            aggressiveness=aggressiveness,
        )

        handlers = [
            ConfigurationHandler(context),
            AccessControlHandler(context),
            DatabaseHandler(context),
            InfrastructureHandler(context),
        ]

        # Containers for script segments
        safe_section = []
        caution_section = []
        review_section = []
        info_section = []
        rollback_section = []

        # Process findings
        for finding in findings:
            for handler in handlers:
                actions = handler.handle(finding)
                if actions:
                    for action in actions:
                        if action.category == "SAFE":
                            safe_section.append(action.script)
                        elif action.category == "CAUTION":
                            caution_section.append(action.script)
                        elif action.category == "REVIEW":
                            review_section.append(action.script)
                        elif action.category == "INFO":
                            info_section.append(action.script)

                        if action.rollback:
                            rollback_section.append(action.rollback)
                    break  # Finding handled by first handler that claims it

        # Finalize handlers (get batched scripts)
        for handler in handlers:
            actions = handler.finalize()
            if actions:
                for action in actions:
                    if action.category == "SAFE":
                        safe_section.append(action.script)
                    elif action.category == "CAUTION":
                        caution_section.append(action.script)
                    elif action.category == "REVIEW":
                        review_section.append(action.script)
                    elif action.category == "INFO":
                        info_section.append(action.script)

                    if action.rollback:
                        rollback_section.append(action.rollback)

        # Add global info scripts (e.g. Encryption Info from InfraHandler)
        infra_handler = next(
            h for h in handlers if isinstance(h, InfrastructureHandler)
        )
        global_infos = infra_handler.get_global_info_scripts()
        for action in global_infos:
            info_section.append(action.script)

        # Build Scripts
        instance_label = context.instance_label

        port_suffix = f"_{port}" if port and port != 1433 else ""
        safe_name = f"{server}{port_suffix}_{inst_id}_{instance or 'default'}".replace(
            "\\", "_"
        ).replace(",", "_")

        main_script = self._build_main_script(
            server,
            instance_label,
            safe_section,
            caution_section,
            review_section,
            info_section,
            port,
        )
        main_path = self.output_dir / f"{safe_name}.sql"
        main_path.write_text("\n".join(main_script), encoding="utf-8")

        rollback_script = self._build_rollback_script(
            server, instance_label, rollback_section
        )
        rollback_path = self.output_dir / f"{safe_name}_ROLLBACK.sql"
        rollback_path.write_text("\n".join(rollback_script), encoding="utf-8")

        # Secrets
        if context.secrets_log:
            secrets_file = (
                self.output_dir
                / f"secrets_{server}_{inst_id}_{instance or 'default'}.txt"
            )
            self._save_secrets_file(
                secrets_file, server, instance_label, context.secrets_log
            )

        # OS Script (PowerShell) - Template
        os_script = infra_handler.generate_os_script()
        os_path = self.output_dir / f"{safe_name}_OS_AUDIT.ps1"
        os_path.write_text(os_script, encoding="utf-8")

        return [main_path, rollback_path, os_path]

    def _build_main_script(
        self,
        server: str,
        instance: str,
        safe_section: list,
        caution_section: list,
        review_section: list,
        info_section: list,
        port: int = 1433,
    ) -> list[str]:
        """Build the main remediation script."""
        lines = [
            "/*",
            "=" * 60,
            "REMEDIATION SCRIPT - AutoDBAudit",
            f"Server: {server}",
            f"Port: {port}",
            f"Instance: {instance}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "INSTRUCTIONS:",
            "1. Review this script before running",
            "2. [AUTO-FIX] sections execute automatically",
            "3. [CAUTION] sections run but log passwords for recovery",
            "4. [REVIEW] sections are commented - uncomment if approved",
            "5. [INFORMATION] sections require manual action",
            "",
            "ROLLBACK: A separate _ROLLBACK.sql file is generated",
            "          to undo changes if needed.",
            "",
            "RUN IN SSMS: Ctrl+T (Results to Text), then F5 (Execute)",
            "=" * 60,
            "*/",
            "",
            "SET NOCOUNT ON;",
            f"PRINT '=== Starting Remediation for {server}\\{instance} ===';",
            f"PRINT 'Execution time: ' + CONVERT(VARCHAR, GETDATE(), 120);",
            "PRINT '';",
        ]

        if safe_section:
            header = self._category_header(
                "⚡ AUTO-FIX", "Safe Remediations (Will Execute)"
            )
            lines.extend([header])
            lines.extend(safe_section)

        if caution_section:
            header = self._category_header(
                "⚠️ CAUTION", "Sensitive Operations (Password Logged)"
            )
            lines.extend([header])
            lines.extend(caution_section)

        if review_section:
            header = self._category_header(
                "👀 REVIEW REQUIRED", "Dangerous Operations (Commented)"
            )
            lines.extend([header])
            lines.extend(
                [
                    "/*",
                    "The following operations require human review.",
                    "Uncomment ONLY if you have verified the action is safe.",
                    "*/",
                    "",
                ]
            )
            lines.extend(review_section)

        if info_section:
            header = self._category_header("ℹ️ INFORMATION", "Manual Actions Required")
            lines.extend([header])
            lines.extend(info_section)

        lines.extend(
            [
                "",
                "PRINT '';",
                "PRINT '=== Remediation Complete ===';",
                "PRINT 'Review output above. Use _ROLLBACK.sql to undo if needed.';",
                "",
            ]
        )
        return lines

    def _build_rollback_script(
        self, server: str, instance: str, rollback_section: list
    ) -> list[str]:
        lines = [
            "/*",
            "=" * 60,
            "ROLLBACK SCRIPT - AutoDBAudit",
            f"Server: {server}",
            f"Instance: {instance}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
            "PURPOSE: Undo changes made by the main remediation script.",
            "",
            "WARNING: Only run this if you need to revert changes!",
            "=" * 60,
            "*/",
            "",
            "SET NOCOUNT ON;",
            f"PRINT '=== ROLLBACK for {server}\\{instance} ===';",
            "PRINT '';",
            "",
        ]

        if rollback_section:
            header = self._category_header(
                "🔙 ROLLBACK", "Undo Operations - Ready to Execute"
            )
            lines.extend([header])
            lines.extend(rollback_section)
        else:
            lines.append("-- No rollback operations generated.")

        lines.extend(["", "PRINT '';", "PRINT '=== Rollback Complete ===';", ""])
        return lines

    def _save_secrets_file(
        self, path: Path, server: str, instance: str, secrets_log: list[str]
    ) -> None:
        content = [
            "=" * 60,
            "SECRETS LOG - DO NOT DISTRIBUTE",
            f"Server: {server}",
            f"Instance: {instance}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
        ]
        content.extend(secrets_log)
        path.write_text("\n".join(content), encoding="utf-8")

    def _category_header(self, tag: str, description: str) -> str:
        return f"""
-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ [{tag}] {description}
-- ╚══════════════════════════════════════════════════════════════════════════╝
"""
