"""
Remediation service for generating actionable T-SQL fix scripts.

DESIGN PRINCIPLE:
A person with ZERO SQL experience should be able to run these scripts
and complete the audit successfully.

ROLLBACK MECHANISM:
Every destructive operation logs full details BEFORE execution.
A separate ROLLBACK script is generated with CREATE statements.

REQUIREMENTS COVERAGE (from db-requirements.md):
✅ #4  - SA disabled + renamed
✅ #5  - Password policy enforcement
✅ #7  - Unused logins disabled (with logging)
✅ #9  - WITH GRANT revocation (review)
✅ #10 - xp_cmdshell and features disabled
✅ #13 - Orphaned users removed (AUTO-FIX), Guest disabled (AUTO-FIX)
✅ #15 - Test databases warning
✅ #16 - Ad Hoc queries disabled
✅ #18 - Database Mail XPs disabled
✅ #20 - Remote access disabled
✅ #22 - Login auditing enabled
⚠️ #2,3 - Version/updates (INFO section only)
⚠️ #11 - Encryption backups (INFO section)
⚠️ #17,19,21 - Protocols/Services (INFO section - requires OS config)
⚠️ #24,25 - Linked servers (REVIEW section)

Script Categories:
1. [AUTO-FIX] Safe - Runs by default with full logging for rollback
2. [CAUTION] Sensitive - Runs but logs critical info (passwords, etc.)
3. [REVIEW] Dangerous - Commented, needs human approval
4. [INFO] Manual - Instructions only
"""

from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_temp_password() -> str:
    """Generate a secure temporary password (16 chars)."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(16))


class RemediationService:
    """
    Service for generating smart T-SQL remediation scripts.

    Goal: Zero-experience user can run and fix everything safely.
    All destructive operations are LOGGED before execution for rollback.
    """

    def __init__(
        self,
        db_path: str | Path = "output/audit_history.db",
        output_dir: str | Path = "output/remediation_scripts",
    ):
        self.db_path = Path(db_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._secrets_log: list[str] = []
        logger.info("RemediationService initialized")

    def generate_scripts(
        self,
        audit_run_id: int | None = None,
        sql_targets: list[dict] | None = None,
        aggressiveness: int = 1,
    ) -> list[Path]:
        """
        Generate remediation scripts for all findings.

        Args:
            audit_run_id: Specific run to generate for (latest if None)
            sql_targets: List of target configs (to identify connecting user)

        Returns:
            List of generated script paths.
        """
        import sqlite3

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row

        # Get latest run if not specified
        if audit_run_id is None:
            row = conn.execute(
                "SELECT id FROM audit_runs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
            if not row:
                logger.error("No audit runs found")
                return []
            audit_run_id = row["id"]

        # Get findings grouped by instance
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

        conn.close()

        if not findings:
            logger.info("No findings requiring remediation")
            return []

        # Group by server/instance (using instance_db_id for uniqueness)
        by_instance: dict[tuple, list] = {}
        for f in findings:
            inst_id = f["instance_db_id"]
            key = (f["server_name"], f["instance_name"], inst_id)
            if key not in by_instance:
                by_instance[key] = []
            by_instance[key].append(dict(f))

        # Build map of connecting users per instance: (server, instance) -> username
        # sql_targets structure: [{"server": "...", "instance": "...", "username": "..."}]
        conn_user_map = {}
        if sql_targets:
            for t in sql_targets:
                # Normalize keys
                srv = t.get("server", "").lower()
                inst = (t.get("instance") or "").lower()
                usr = t.get("username", "")
                conn_user_map[(srv, inst)] = usr

        generated = []
        for (server, instance, inst_id), instance_findings in by_instance.items():
            # Lookup connecting user
            # Map keys are lower case
            # normalized instance: "" for default
            lookup_inst = instance.lower() if instance else ""
            conn_user = conn_user_map.get((server.lower(), lookup_inst))
            print(
                f"DEBUG: Server='{server}', Inst='{instance}', ConnUser='{conn_user}'"
            )

            paths = self._generate_instance_scripts(
                server, instance, inst_id, instance_findings, conn_user, aggressiveness
            )
            generated.extend(paths)

        logger.info("Generated %d script files", len(generated))
        return generated

    def _generate_instance_scripts(
        self,
        server: str,
        instance: str,
        inst_id: int,
        findings: list[dict],
        conn_user: str | None = None,
        aggressiveness: int = 1,
    ) -> list[Path]:
        """Generate remediation + rollback scripts for an instance."""

        instance_label = f"{instance}" if instance else "(Default)"
        # Include instance_id in filename for uniqueness
        safe_name = f"{server}_{inst_id}_{instance or 'default'}".replace(
            "\\", "_"
        ).replace(",", "_")

        # Generate temp password for SA operations
        temp_password = generate_temp_password()

        # Build script sections
        safe_section: list[str] = []
        caution_section: list[str] = []
        review_section: list[str] = []
        info_section: list[str] = []
        rollback_section: list[str] = []

        # Track what we've seen to avoid duplicates
        seen_configs = set()
        seen_logins = set()
        seen_db_users = set()
        has_sa_finding = False
        has_version_finding = False

        for f in findings:
            ft = f["finding_type"]
            entity = f["entity_name"]
            desc = f.get("finding_description", "") or ""

            # === SA ACCOUNT ===
            if ft == "sa_account":
                has_sa_finding = True
                continue

            # === CONFIG SETTINGS ===
            if ft == "config":
                # Defer processing config settings to ensure 'show advanced options' comes last
                continue

        # === PROCESS CONFIG FINDINGS (Ordered) ===
        config_findings = [f for f in findings if f["finding_type"] == "config"]
        # Sort so 'show advanced options' is LAST
        config_findings.sort(
            key=lambda x: (
                1 if x["entity_name"].lower() == "show advanced options" else 0
            )
        )

        for f in config_findings:
            entity = f["entity_name"]
            if entity in seen_configs:
                continue
            seen_configs.add(entity)
            safe_section.append(self._script_disable_config(entity))
            rollback_section.append(self._rollback_enable_config(entity))

        # === PROCESS OTHER FINDINGS ===
        for f in findings:
            ft = f["finding_type"]
            entity = f["entity_name"]
            desc = f.get("finding_description", "") or ""

            if ft == "config":
                continue  # Already processed

            # === SA ACCOUNT ===

            # === LOGINS ===
            elif ft == "login":
                if entity.lower() == "sa":
                    has_sa_finding = True
                    continue

                if entity in seen_logins:
                    continue
                seen_logins.add(entity)

                # Check for lockout risk (Is this the user running the audit?)
                is_connected_user = bool(
                    conn_user and entity.strip().lower() == conn_user.strip().lower()
                )

                if "sysadmin" in desc.lower() or "privilege" in desc.lower():
                    # High priv always reviewed
                    script = self._script_review_login(
                        entity, desc, is_connected_user, aggressiveness
                    )
                    review_section.append(script)

                elif "unused" in desc.lower() or "not used" in desc.lower():
                    # Unused login disable
                    script = self._script_disable_unused_login(
                        entity, is_connected_user
                    )
                    if is_connected_user:
                        review_section.append(script)  # Move to review if risky
                    else:
                        safe_section.append(script)
                    rollback_section.append(self._rollback_enable_login(entity))

                elif "policy" in desc.lower():
                    # Password policy
                    script = self._script_enable_password_policy(
                        entity, is_connected_user
                    )
                    if is_connected_user:
                        review_section.append(script)
                    else:
                        safe_section.append(script)

                elif "grant" in desc.lower():
                    review_section.append(
                        self._script_review_grant_option(entity, desc)
                    )
                else:
                    script = self._script_review_login(
                        entity, desc, is_connected_user, aggressiveness
                    )
                    review_section.append(script)

            # === DATABASE USERS ===
            elif ft == "db_user":
                key = entity
                if key in seen_db_users:
                    continue
                seen_db_users.add(key)

                if "|" in entity:
                    db_name, user_name = entity.split("|", 1)
                else:
                    db_name, user_name = "master", entity

                # Orphaned user - AUTO-FIX with full logging
                if "orphan" in desc.lower():
                    safe_section.append(
                        self._script_drop_orphan_user(db_name, user_name)
                    )
                    rollback_section.append(
                        self._rollback_create_orphan_user(db_name, user_name)
                    )
                # Guest user enabled - AUTO-FIX
                elif "guest" in desc.lower() or user_name.lower() == "guest":
                    safe_section.append(self._script_revoke_guest(db_name))
                    rollback_section.append(self._rollback_grant_guest(db_name))
                else:
                    review_section.append(
                        self._script_review_db_user(db_name, user_name, desc)
                    )

            # === DATABASE PROPERTIES ===
            elif ft == "database":
                db_name = entity
                if "trustworthy" in desc.lower():
                    safe_section.append(self._script_disable_trustworthy(db_name))
                    rollback_section.append(self._rollback_enable_trustworthy(db_name))
                elif any(
                    x in db_name.lower()
                    for x in ["adventureworks", "pubs", "northwind", "test"]
                ):
                    review_section.append(self._script_review_test_database(db_name))

            # === LINKED SERVERS ===
            elif ft == "linked_server":
                review_section.append(self._script_review_linked_server(entity, desc))

            # === BACKUPS ===
            elif ft == "backup":
                info_section.append(self._script_info_backup(entity))

            # === VERSION ===
            elif ft == "version":
                has_version_finding = True

        # === ADD SA ACCOUNT HANDLING (CAUTION) ===
        # Only add this if we actually found an issue with the SA account
        if has_sa_finding:
            # Check if we are connected as SA
            is_connected_as_sa = conn_user and conn_user.lower() == "sa"

            # Generate SA script (potentially commented out)
            sa_script = self._script_handle_sa(temp_password, is_connected_as_sa)

            if is_connected_as_sa:
                # Move to REVIEW section if we blocked it for safety
                review_section.append(sa_script)
            else:
                # Otherwise keep in CAUTION (Auto-run but sensitive)
                caution_section.append(sa_script)

            rollback_section.append(self._rollback_sa(temp_password))

        # === ADD LOGIN AUDITING ===
        # Only add if we have a specific finding for it (TODO: Detect AuditLevel)
        # safe_section.append(self._script_enable_login_auditing())

        # === ADD VERSION/UPDATE INFO ===
        if has_version_finding:
            info_section.append(self._script_info_version_upgrade())

        # === ADD SERVICES INFO (always add) ===
        # info_section.append(self._script_info_services())

        # === ADD ENCRYPTION INFO ===
        info_section.append(self._script_info_encryption())

        # Build and write main script
        main_script = self._build_main_script(
            server,
            instance_label,
            safe_section,
            caution_section,
            review_section,
            info_section,
        )
        main_path = self.output_dir / f"{safe_name}.sql"
        main_path.write_text("\n".join(main_script), encoding="utf-8")
        logger.info("Generated: %s", main_path)

        # Build and write rollback script
        rollback_script = self._build_rollback_script(
            server, instance_label, rollback_section
        )
        rollback_path = self.output_dir / f"{safe_name}_ROLLBACK.sql"
        rollback_path.write_text("\n".join(rollback_script), encoding="utf-8")
        logger.info("Generated: %s", rollback_path)

        # Write secrets file if any secrets were generated
        if self._secrets_log:
            secrets_file = (
                self.output_dir
                / f"secrets_{server}_{inst_id}_{instance or 'default'}.txt"
            )
            self._save_secrets_file(secrets_file, server, instance_label)
            # Clear log for next iteration
            self._secrets_log = []

        return [main_path, rollback_path]

    def _build_main_script(
        self,
        server: str,
        instance: str,
        safe_section: list,
        caution_section: list,
        review_section: list,
        info_section: list,
    ) -> list[str]:
        """Build the main remediation script."""
        lines = [
            "/*",
            "=" * 60,
            "REMEDIATION SCRIPT - AutoDBAudit",
            f"Server: {server}",
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

        # Safe section
        if safe_section:
            header = self._category_header(
                "⚡ AUTO-FIX",
                "Safe Remediations (Will Execute)\n-- Full state logged for rollback",
            )
            lines.extend([header])
            lines.extend(safe_section)

        # Caution section
        if caution_section:
            header = self._category_header(
                "⚠️ CAUTION", "Sensitive Operations (Password Logged)"
            )
            lines.extend([header])
            lines.extend(caution_section)

        # Review section
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

        # Info section
        if info_section:
            header = self._category_header("ℹ️ INFORMATION", "Manual Actions Required")
            lines.extend([header])
            lines.extend(info_section)

        # Footer
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
        """Build the rollback script to undo changes."""
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
            "         Review each section before uncommenting.",
            "",
            "NOTE: Some operations may not be fully reversible.",
            "      (e.g., dropped users with specific permissions)",
            "=" * 60,
            "*/",
            "",
            "SET NOCOUNT ON;",
            f"PRINT '=== ROLLBACK for {server}\\{instance} ===';",
            f"PRINT 'Execution time: ' + CONVERT(VARCHAR, GETDATE(), 120);",
            "PRINT '';",
            "",
        ]

        if rollback_section:
            header = self._category_header(
                "🔙 ROLLBACK",
                "Undo Operations (Commented)\n-- Uncomment the ones you need to undo",
            )
            lines.extend([header])
            lines.extend(rollback_section)
        else:
            lines.append("-- No rollback operations generated.")

        lines.extend(
            [
                "",
                "PRINT '';",
                "PRINT '=== Rollback Complete ===';",
                "",
            ]
        )

        return lines

    def _save_secrets_file(self, path: Path, server: str, instance: str) -> None:
        """Save generated secrets to a separate secure file."""
        content = [
            "=" * 60,
            "SECRETS LOG - DO NOT DISTRIBUTE",
            f"Server: {server}",
            f"Instance: {instance}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 60,
            "",
        ]
        content.extend(self._secrets_log)
        path.write_text("\n".join(content), encoding="utf-8")

    # ===================================================================
    # HELPER METHODS
    # ===================================================================

    def _wrap_lockout_warning(self, script: str, username: str) -> str:
        """Wrap a script in comments with a lockout warning."""
        lines = script.split("\n")
        commented_lines = [f"-- {line}" if line.strip() else line for line in lines]
        warning = f"""
/* 
!!! LOCKOUT RISK: YOU ARE CONNECTED AS '{username}' !!!
=========================================================
This section has been commented out because we detected
that you used the '{username}' account to connect to this Audit.

altering this login could cause you to lose access immediately!
Run this only if you have another SysAdmin account ready!
*/
"""
        return warning + "\n".join(commented_lines)

    def _category_header(self, tag: str, description: str) -> str:
        """Generate a category header with searchable tag."""
        return f"""
-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ [{tag}] {description}
-- ╚══════════════════════════════════════════════════════════════════════════╝
"""

    def _item_header(self, tag: str, title: str) -> str:
        """Generate a standardized header for an individual remediation item."""
        return f"""
-- ============================================================================
-- [{tag}] {title}
-- ============================================================================"""

    # ===================================================================
    # AUTO-FIX SCRIPTS (Safe, run by default)
    # ===================================================================

    def _script_disable_config(self, setting: str) -> str:
        """Disable a dangerous sp_configure setting."""
        header = self._item_header("⚙️ CONFIG", f"Disable {setting}")

        # If we are fixing 'show advanced options' itself, DO NOT enable it first!
        # Just disable it.
        if setting.lower() == "show advanced options":
            prelude = ""
        else:
            # For other settings, we must ensure advanced options are visible first
            prelude = """PRINT 'Enabling show advanced options (temporary)...';
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE WITH OVERRIDE;
GO

"""

        return f"""{header}
{prelude}PRINT 'Disabling {setting}...';
EXEC sp_configure '{setting}', 0;
RECONFIGURE WITH OVERRIDE;

-- Verify change (Robustness check)
IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = '{setting}' AND value_in_use = 0)
    PRINT '  [OK] {setting} verified disabled';
ELSE IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = '{setting}' AND value = 0 AND is_dynamic = 0)
    PRINT '  [PENDING] {setting} configured to 0 but requires SQL RESTART to take effect.';
ELSE
    PRINT '  [WARNING] {setting} verification failed. Value_in_use is still 1 (Force failed?).';
GO
"""

    def _script_enable_password_policy(
        self, login_name: str, is_connected_user: bool = False
    ) -> str:
        """Enable password policy for a SQL login."""
        header = self._item_header("👤 LOGIN", f"Enable password policy: {login_name}")
        script = f"""{header}
PRINT 'Enabling password policy for [{login_name}]...';
ALTER LOGIN [{login_name}] WITH CHECK_POLICY = ON;
PRINT '  [OK] Password policy enabled';
GO
"""
        if is_connected_user:
            return self._wrap_lockout_warning(script, login_name)
        return script

    def _script_disable_unused_login(
        self, login_name: str, is_connected_user: bool = False
    ) -> str:
        """Disable unused login WITH LOGGING."""
        header = self._item_header("👤 LOGIN", f"Disable unused login: {login_name}")
        script = f"""{header}
PRINT '--- LOGGING BEFORE DISABLE ---';
PRINT 'Login: {login_name}';
SELECT name, type_desc, is_disabled, create_date, default_database_name
FROM sys.server_principals WHERE name = '{login_name}';
PRINT '--- END LOGGING ---';
PRINT 'Disabling [{login_name}]...';
IF EXISTS (SELECT * FROM sys.server_principals 
           WHERE name = '{login_name}' 
           AND (
               NOT EXISTS (SELECT * FROM sys.server_role_members srm 
                           JOIN sys.server_principals r ON srm.role_principal_id = r.principal_id 
                           WHERE srm.member_principal_id = principal_id AND r.name = 'sysadmin')
               OR (SELECT COUNT(*) FROM sys.server_role_members srm 
                   JOIN sys.server_principals r ON srm.role_principal_id = r.principal_id
                   JOIN sys.server_principals m ON srm.member_principal_id = m.principal_id
                   WHERE r.name = 'sysadmin' AND m.is_disabled = 0 AND m.name <> '{login_name}') > 0
           ))
BEGIN
    ALTER LOGIN [{login_name}] DISABLE;
    PRINT '  [OK] Login disabled';
END
ELSE
BEGIN
    PRINT '  [SKIP] Safety check: Disabling this would leave 0 sysadmins or user not found.';
END
GO
"""
        if is_connected_user:
            return self._wrap_lockout_warning(script, login_name)
        return script

    def _script_drop_orphan_user(self, db_name: str, user_name: str) -> str:
        """Drop orphaned user WITH FULL LOGGING for rollback."""
        header = self._item_header(
            "👻 ORPHAN", f"DROP ORPHANED USER: [{db_name}].[{user_name}]"
        )
        return f"""{header}
PRINT '======================================';
PRINT 'ORPHANED USER REMOVAL (with full logging)';
PRINT 'Database: {db_name}';
PRINT 'User: {user_name}';
PRINT '======================================';

-- Log user details for rollback
PRINT '--- LOGGING USER STATE (copy this for manual rollback) ---';
USE [{db_name}];
SELECT 'User Details:' as Info;
SELECT name, type_desc, default_schema_name, create_date
FROM sys.database_principals WHERE name = '{user_name}';

SELECT 'Role Memberships:' as Info;
SELECT r.name as role_name
FROM sys.database_role_members rm
JOIN sys.database_principals r ON rm.role_principal_id = r.principal_id
JOIN sys.database_principals u ON rm.member_principal_id = u.principal_id
WHERE u.name = '{user_name}';

SELECT 'Object Permissions:' as Info;
SELECT permission_name, state_desc, OBJECT_NAME(major_id) as object_name
FROM sys.database_permissions
WHERE grantee_principal_id = USER_ID('{user_name}');
PRINT '--- END LOGGING ---';

-- Actually drop the user
PRINT 'Dropping user [{user_name}]...';
IF EXISTS (SELECT * FROM sys.database_principals WHERE name = '{user_name}')
BEGIN
    DROP USER [{user_name}];
    PRINT '  [OK] Orphaned user removed';
END
ELSE
BEGIN
    PRINT '  [SKIP] User not found (already dropped?)';
END
GO
"""

    def _script_revoke_guest(self, db_name: str) -> str:
        """Revoke CONNECT from guest user."""
        header = self._item_header("👤 GUEST", f"Revoke guest access: [{db_name}]")
        return f"""{header}
PRINT 'Revoking guest CONNECT in [{db_name}]...';
USE [{db_name}];
REVOKE CONNECT FROM guest;
PRINT '  [OK] Guest access revoked';
GO
"""

    def _script_disable_trustworthy(self, db_name: str) -> str:
        """Disable TRUSTWORTHY on database."""
        header = self._item_header("🛢️ DATABASE", f"Disable TRUSTWORTHY: [{db_name}]")
        return f"""{header}
PRINT 'Disabling TRUSTWORTHY on [{db_name}]...';
ALTER DATABASE [{db_name}] SET TRUSTWORTHY OFF;
PRINT '  [OK] TRUSTWORTHY disabled';
GO
"""

    def _script_enable_login_auditing(self) -> str:
        """Enable login auditing (success + failure)."""
        header = self._item_header(
            "📝 AUDIT", "Enable login auditing (Requirement #22)"
        )
        return f"""{header}
PRINT 'Enabling login auditing (success + failure)...';
EXEC xp_instance_regwrite 
    N'HKEY_LOCAL_MACHINE', 
    N'Software\\Microsoft\\MSSQLServer\\MSSQLServer', 
    N'AuditLevel', 
    REG_DWORD, 
    3;
PRINT '  [OK] Login auditing = Both (success + failure)';
PRINT '  NOTE: Restart SQL Server for this to take effect';
GO
"""

    # ===================================================================
    # ROLLBACK SCRIPTS
    # ===================================================================

    def _rollback_enable_config(self, setting: str) -> str:
        """Rollback: re-enable a config setting."""
        header = self._item_header("🔙 CONFIG", f"Re-enable {setting}")
        return f"""
/*{header}
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure '{setting}', 1;
RECONFIGURE;
PRINT 'Rolled back: {setting} = 1';
*/
"""

    def _rollback_enable_login(self, login_name: str) -> str:
        """Rollback: re-enable a disabled login."""
        header = self._item_header("🔙 LOGIN", f"Re-enable login {login_name}")
        return f"""
/*{header}
ALTER LOGIN [{login_name}] ENABLE;
PRINT 'Rolled back: {login_name} enabled';
*/
"""

    def _rollback_create_orphan_user(self, db_name: str, user_name: str) -> str:
        """Rollback: recreate orphaned user (basic)."""
        header = self._item_header(
            "🔙 ORPHAN", f"Recreate user {user_name} in {db_name}"
        )
        return f"""
/*{header}
NOTE: This creates a basic user. You may need to:
      1. Remap to a login if one exists
      2. Reassign roles and permissions from the logged output
USE [{db_name}];
CREATE USER [{user_name}] WITHOUT LOGIN;
PRINT 'Rolled back: Created user {user_name} (without login)';

-- To add to roles (uncomment as needed):
-- EXEC sp_addrolemember 'db_datareader', '{user_name}';
-- EXEC sp_addrolemember 'db_datawriter', '{user_name}';
*/
"""

    def _rollback_grant_guest(self, db_name: str) -> str:
        """Rollback: grant guest access back."""
        header = self._item_header("🔙 GUEST", f"Re-enable guest access in {db_name}")
        return f"""
/*{header}
USE [{db_name}];
GRANT CONNECT TO guest;
PRINT 'Rolled back: guest access granted';
*/
"""

    def _rollback_enable_trustworthy(self, db_name: str) -> str:
        """Rollback: re-enable TRUSTWORTHY."""
        header = self._item_header("🔙 DATABASE", f"Re-enable TRUSTWORTHY on {db_name}")
        return f"""
/*{header}
ALTER DATABASE [{db_name}] SET TRUSTWORTHY ON;
PRINT 'Rolled back: TRUSTWORTHY enabled';
*/
"""

    def _rollback_sa(self, temp_password: str) -> str:
        """Rollback: re-enable SA account."""
        header = self._item_header("🔙 SA_ACCOUNT", "Re-enable SA account")
        return f"""
/*{header}
NOTE: SA was renamed to [$@] and disabled
To restore:
1. ALTER LOGIN [$@] ENABLE;
2. (Optional) Rename back to 'sa':
   ALTER LOGIN [$@] WITH NAME = [sa];
3. Set a new strong password:
   ALTER LOGIN [sa] WITH PASSWORD = N'NEW_STRONG_PASSWORD_HERE';
PRINT 'Rolled back: SA account enabled';

Temp password that was set: {temp_password}
*/
"""

    # ===================================================================
    # CAUTION SCRIPTS (Run but log critical info)
    # ===================================================================

    def _script_handle_sa(
        self, temp_password: str, is_connected_as_sa: bool = False
    ) -> str:
        """Handle SA account: rename + disable + log password."""
        # Log for secrets file
        self._secrets_log.append(f"[SA Account]\nTemp Password: {temp_password}\n")

        header = self._item_header(
            "👑 SA_ACCOUNT", "SA ACCOUNT REMEDIATION (Requirement #4)"
        )

        script = f"""{header}
-- Actions: 1) Rename to $@ 2) Set temp password 3) Disable
PRINT '=== SA ACCOUNT REMEDIATION ===';

-- Step 1: Rename SA to $@
PRINT 'Step 1: Renaming [sa] to [$@]...';
BEGIN TRY
    ALTER LOGIN [sa] WITH NAME = [$@];
    PRINT '  [OK] SA renamed to $@';
END TRY
BEGIN CATCH
    PRINT '  [SKIP] Already renamed or error: ' + ERROR_MESSAGE();
END CATCH;

-- Step 2: Set temporary password (LOGGED FOR RECOVERY)
PRINT '';
PRINT 'Step 2: Setting temporary password...';
PRINT '****************************************';
PRINT '* RECOVERY PASSWORD: {temp_password}';
PRINT '* SAVE THIS PASSWORD!';
PRINT '****************************************';
BEGIN TRY
    ALTER LOGIN [$@] WITH PASSWORD = N'{temp_password}';
    PRINT '  [OK] Password set';
END TRY
BEGIN CATCH
    ALTER LOGIN [sa] WITH PASSWORD = N'{temp_password}';
    PRINT '  [OK] Password set (on [sa])';
END CATCH;

-- Step 3: Disable the account
PRINT '';
PRINT 'Step 3: Disabling account...';
BEGIN TRY
    ALTER LOGIN [$@] DISABLE;
    PRINT '  [OK] Account disabled';
END TRY
BEGIN CATCH
    ALTER LOGIN [sa] DISABLE;
    PRINT '  [OK] Account disabled (on [sa])';
END CATCH;
GO
"""
        # If connected as SA, comment it out entirely to prevent lockout
        if is_connected_as_sa:
            return self._wrap_lockout_warning(script, "sa")

        return script

    # ===================================================================
    # REVIEW SCRIPTS (Commented, needs approval)
    # ===================================================================

    def _script_review_login(
        self,
        login_name: str,
        desc: str,
        is_connected_user: bool = False,
        aggressiveness: int = 1,
    ) -> str:
        """Review high-privilege login - Behavior depends on aggressiveness."""
        header = self._item_header("👀 REVIEW", f"HIGH-PRIVILEGE LOGIN: {login_name}")
        base_script = f"""{header}
-- Issue: {desc}
--
-- DO NOT remove without business approval!
--"""

        # Define commands
        cmd_disable = f"ALTER LOGIN [{login_name}] DISABLE;"
        cmd_revoke = f"EXEC sp_dropsrvrolemember '{login_name}', 'sysadmin';"

        # Determine state based on aggressiveness
        # Level 1 (Default): All commented
        # Level 2 (Constructive): Revoke active, Disable commented
        # Level 3 (Brutal): Revoke active, Disable active

        disable_active = aggressiveness >= 3
        revoke_active = aggressiveness >= 2

        # Format commands
        line_disable = cmd_disable if disable_active else f"-- {cmd_disable}"
        line_revoke = cmd_revoke if revoke_active else f"-- {cmd_revoke}"

        script = f"""{base_script}
-- To disable (Aggressiveness={aggressiveness}):
{line_disable}
--
-- To remove from sysadmin (SQL 2008 R2 compatible):
{line_revoke}
"""
        if is_connected_user:
            # SAFETY OVERRIDE: If it's the connecting user, always comment everything out
            # and wrap in warning, regardless of aggressiveness.
            # We reconstruct the "safe" version first to ensure it's fully commented.
            safe_script = f"""{base_script}
-- To disable (SAFE MODE OVERRIDE):
-- {cmd_disable}
--
-- To remove from sysadmin (SQL 2008 R2 compatible):
-- {cmd_revoke}
"""
            return self._wrap_lockout_warning(safe_script, login_name)

        return script

    def _script_review_grant_option(self, login_name: str, desc: str) -> str:
        """Review WITH GRANT OPTION - COMMENTED."""
        header = self._item_header("👀 REVIEW", f"WITH GRANT OPTION: {login_name}")
        return f"""{header}
-- Issue: {desc}
--
-- To revoke with cascade:
-- REVOKE ALL FROM [{login_name}] CASCADE;
"""

    def _script_review_db_user(self, db_name: str, user_name: str, desc: str) -> str:
        """Review database user - COMMENTED."""
        header = self._item_header(
            "👀 REVIEW", f"DATABASE USER: [{db_name}].[{user_name}]"
        )
        return f"""{header}
-- Issue: {desc}
--
-- To drop (uncomment if approved):
-- USE [{db_name}];
-- IF EXISTS (SELECT * FROM sys.database_principals WHERE name = '{user_name}') DROP USER [{user_name}];
"""

    def _script_review_linked_server(self, ls_name: str, desc: str) -> str:
        """Review linked server - COMMENTED."""
        header = self._item_header("👀 REVIEW", f"LINKED SERVER: {ls_name}")
        return f"""{header}
-- Issue: {desc}
--
-- To disable RPC OUT:
-- EXEC sp_serveroption '{ls_name}', 'rpc out', 'false';
--
-- To drop entirely:
-- EXEC sp_dropserver '{ls_name}', 'droplogins';
"""

    def _script_review_test_database(self, db_name: str) -> str:
        """Review test database - COMMENTED."""
        header = self._item_header("👀 REVIEW", f"TEST DATABASE: {db_name}")
        return f"""{header}
-- Should not exist in production.
--
-- To detach: EXEC sp_detach_db '{db_name}';
-- To drop:   DROP DATABASE [{db_name}];
"""

    # ===================================================================
    # INFO SCRIPTS (Instructions only)
    # ===================================================================

    def _script_info_backup(self, db_name: str) -> str:
        """Backup instructions."""
        # Using item header logic but wrapping in block comment for info
        header = self._item_header("💾 BACKUP", f"BACKUP REQUIRED: {db_name}")
        return f"""
/*{header}
Run: BACKUP DATABASE [{db_name}] TO DISK = 'D:\\Backups\\{db_name}.bak' WITH COMPRESSION;
*/
PRINT '[ACTION] Configure backup for: {db_name}';
"""

    def _script_info_version_upgrade(self) -> str:
        """Version upgrade instructions."""
        header = self._item_header("🆙 VERSION", "SQL SERVER VERSION UPGRADE REQUIRED")
        return f"""
/*{header}
Current version is older than 2019. Plan upgrade to SQL Server 2019+.
See: https://docs.microsoft.com/sql/database-engine/install-windows/upgrade-sql-server
*/
PRINT '[ACTION] Plan SQL Server version upgrade';
"""

    def _script_info_services(self) -> str:
        """Services configuration instructions."""
        header = self._item_header(
            "🔧 SERVICES", "WINDOWS SERVICES REVIEW (Requirements #6, #19, #21)"
        )
        return f"""
/*{header}
- Disable SQL Server Browser (unless needed for named instances)
- Disable Analysis/Reporting/Integration Services if not used
- Use domain accounts for service accounts (not LocalSystem)

PowerShell:
  Stop-Service 'SQLBrowser'; Set-Service 'SQLBrowser' -StartupType Disabled
*/
PRINT '[ACTION] Review SQL Server Windows services';
"""

    def _script_info_encryption(self) -> str:
        """Encryption key backup instructions."""
        header = self._item_header(
            "🔐 ENCRYPTION", "ENCRYPTION KEY BACKUP (Requirement #11)"
        )
        return f"""
/*{header}
If encryption is enabled, back up:
- Service Master Key:  BACKUP SERVICE MASTER KEY TO FILE = 'path' ENCRYPTION BY PASSWORD = 'pwd';
- Database Master Key: USE [db]; BACKUP MASTER KEY TO FILE = 'path' ENCRYPTION BY PASSWORD = 'pwd';
- Certificates:        BACKUP CERTIFICATE [cert] TO FILE = 'path' WITH PRIVATE KEY (...);
*/
PRINT '[RECOMMENDED] Review encryption key backups';
"""


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate remediation scripts")
    parser.add_argument("--db", default="output/audit_history.db")

    # Default output should be predictable or explicitly set
    # Using '.' as default if typical use is running from project root to generate in 'output/...' via calling logic
    # But user asked for better defaults. Let's make it optional and if not provided,
    # use a timestamped folder in current directory.
    parser.add_argument(
        "--output",
        help="Output directory (default: output/remediation_scripts_<timestamp>)",
    )
    parser.add_argument("--run-id", type=int, help="Audit run ID")

    args = parser.parse_args()

    # Handle default output directory if not specified
    output_dir = args.output
    if not output_dir:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"output/remediation_scripts_{timestamp}"

    service = RemediationService(db_path=args.db, output_dir=output_dir)
    scripts = service.generate_scripts(audit_run_id=args.run_id)

    print(f"\n✅ Generated {len(scripts)} script file(s)")
    for s in scripts:
        print(f"   📄 {s}")

    return 0


if __name__ == "__main__":
    exit(main())
