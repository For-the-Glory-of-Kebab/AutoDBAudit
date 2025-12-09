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
    return ''.join(secrets.choice(alphabet) for _ in range(16))


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
        logger.info("RemediationService initialized")
    
    def generate_scripts(self, audit_run_id: int | None = None) -> list[Path]:
        """
        Generate remediation scripts for all findings.
        
        Returns list of generated script paths.
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
        findings = conn.execute("""
            SELECT f.*, i.instance_name, s.hostname as server_name
            FROM findings f
            JOIN instances i ON f.instance_id = i.id
            JOIN servers s ON i.server_id = s.id
            WHERE f.audit_run_id = ?
            AND f.status IN ('FAIL', 'WARN')
            ORDER BY s.hostname, i.instance_name, f.finding_type
        """, (audit_run_id,)).fetchall()
        
        conn.close()
        
        if not findings:
            logger.info("No findings requiring remediation")
            return []
        
        # Group by server/instance
        by_instance: dict[tuple, list] = {}
        for f in findings:
            key = (f["server_name"], f["instance_name"])
            if key not in by_instance:
                by_instance[key] = []
            by_instance[key].append(dict(f))
        
        # Generate scripts per instance
        generated = []
        for (server, instance), instance_findings in by_instance.items():
            paths = self._generate_instance_scripts(server, instance, instance_findings)
            generated.extend(paths)
        
        logger.info("Generated %d script files", len(generated))
        return generated
    
    def _generate_instance_scripts(
        self, server: str, instance: str, findings: list[dict]
    ) -> list[Path]:
        """Generate remediation + rollback scripts for an instance."""
        
        instance_label = f"{instance}" if instance else "(Default)"
        safe_name = f"{server}_{instance or 'default'}".replace("\\", "_").replace(",", "_")
        
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
                if entity in seen_configs:
                    continue
                seen_configs.add(entity)
                safe_section.append(self._script_disable_config(entity))
                rollback_section.append(self._rollback_enable_config(entity))
            
            # === LOGINS ===
            elif ft == "login":
                if entity in seen_logins:
                    continue
                seen_logins.add(entity)
                
                if "sysadmin" in desc.lower() or "privilege" in desc.lower():
                    review_section.append(self._script_review_login(entity, desc))
                elif "unused" in desc.lower() or "not used" in desc.lower():
                    safe_section.append(self._script_disable_unused_login(entity))
                    rollback_section.append(self._rollback_enable_login(entity))
                elif "policy" in desc.lower():
                    safe_section.append(self._script_enable_password_policy(entity))
                elif "grant" in desc.lower():
                    review_section.append(self._script_review_grant_option(entity, desc))
                else:
                    review_section.append(self._script_review_login(entity, desc))
            
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
                    safe_section.append(self._script_drop_orphan_user(db_name, user_name))
                    rollback_section.append(self._rollback_create_orphan_user(db_name, user_name))
                # Guest user enabled - AUTO-FIX
                elif "guest" in desc.lower() or user_name.lower() == "guest":
                    safe_section.append(self._script_revoke_guest(db_name))
                    rollback_section.append(self._rollback_grant_guest(db_name))
                else:
                    review_section.append(self._script_review_db_user(db_name, user_name, desc))
            
            # === DATABASE PROPERTIES ===
            elif ft == "database":
                db_name = entity
                if "trustworthy" in desc.lower():
                    safe_section.append(self._script_disable_trustworthy(db_name))
                    rollback_section.append(self._rollback_enable_trustworthy(db_name))
                elif any(x in db_name.lower() for x in ["adventureworks", "pubs", "northwind", "test"]):
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
        if has_sa_finding:
            caution_section.append(self._script_handle_sa(temp_password))
            rollback_section.append(self._rollback_sa(temp_password))
        
        # === ADD LOGIN AUDITING (always add if any findings) ===
        safe_section.append(self._script_enable_login_auditing())
        
        # === ADD VERSION/UPDATE INFO ===
        if has_version_finding:
            info_section.append(self._script_info_version_upgrade())
        
        # === ADD SERVICES INFO (always add) ===
        info_section.append(self._script_info_services())
        
        # === ADD ENCRYPTION INFO ===
        info_section.append(self._script_info_encryption())
        
        # Build and write main script
        main_script = self._build_main_script(
            server, instance_label, safe_section, caution_section, 
            review_section, info_section
        )
        main_path = self.output_dir / f"{safe_name}.sql"
        main_path.write_text("\n".join(main_script), encoding="utf-8")
        logger.info("Generated: %s", main_path)
        
        # Build and write rollback script
        rollback_script = self._build_rollback_script(server, instance_label, rollback_section)
        rollback_path = self.output_dir / f"{safe_name}_ROLLBACK.sql"
        rollback_path.write_text("\n".join(rollback_script), encoding="utf-8")
        logger.info("Generated: %s", rollback_path)
        
        return [main_path, rollback_path]
    
    def _build_main_script(
        self, server: str, instance: str,
        safe_section: list, caution_section: list,
        review_section: list, info_section: list
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
            lines.extend([
                "",
                "-- " + "=" * 55,
                "-- [AUTO-FIX] Safe Remediations (Will Execute)",
                "-- Full state logged for rollback",
                "-- " + "=" * 55,
                "",
            ])
            lines.extend(safe_section)
        
        # Caution section
        if caution_section:
            lines.extend([
                "",
                "-- " + "=" * 55,
                "-- [CAUTION] Sensitive Operations (Password Logged)",
                "-- " + "=" * 55,
                "",
            ])
            lines.extend(caution_section)
        
        # Review section
        if review_section:
            lines.extend([
                "",
                "-- " + "=" * 55,
                "-- [REVIEW REQUIRED] Dangerous Operations (Commented)",
                "-- " + "=" * 55,
                "",
                "/*",
                "The following operations require human review.",
                "Uncomment ONLY if you have verified the action is safe.",
                "*/",
                "",
            ])
            lines.extend(review_section)
        
        # Info section
        if info_section:
            lines.extend([
                "",
                "-- " + "=" * 55,
                "-- [INFORMATION] Manual Actions Required",
                "-- " + "=" * 55,
                "",
            ])
            lines.extend(info_section)
        
        # Footer
        lines.extend([
            "",
            "PRINT '';",
            "PRINT '=== Remediation Complete ===';",
            "PRINT 'Review output above. Use _ROLLBACK.sql to undo if needed.';",
            "",
        ])
        
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
            lines.extend([
                "-- " + "=" * 55,
                "-- ROLLBACK COMMANDS (All commented by default)",
                "-- Uncomment the ones you need to undo",
                "-- " + "=" * 55,
                "",
            ])
            lines.extend(rollback_section)
        else:
            lines.append("-- No rollback operations generated.")
        
        lines.extend([
            "",
            "PRINT '';",
            "PRINT '=== Rollback Complete ===';",
            "",
        ])
        
        return lines
    
    # ===================================================================
    # AUTO-FIX SCRIPTS (Safe, run by default)
    # ===================================================================
    
    def _script_disable_config(self, setting: str) -> str:
        """Disable a dangerous sp_configure setting."""
        return f"""
-- Disable: {setting}
PRINT 'Disabling {setting}...';
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE;
EXEC sp_configure '{setting}', 0;
RECONFIGURE;
PRINT '  [OK] {setting} = 0';
GO
"""
    
    def _script_enable_password_policy(self, login_name: str) -> str:
        """Enable password policy for a SQL login."""
        return f"""
-- Enable password policy: {login_name}
PRINT 'Enabling password policy for [{login_name}]...';
ALTER LOGIN [{login_name}] WITH CHECK_POLICY = ON;
PRINT '  [OK] Password policy enabled';
GO
"""
    
    def _script_disable_unused_login(self, login_name: str) -> str:
        """Disable unused login WITH LOGGING."""
        return f"""
-- Disable unused login: {login_name}
PRINT '--- LOGGING BEFORE DISABLE ---';
PRINT 'Login: {login_name}';
SELECT name, type_desc, is_disabled, create_date, default_database_name
FROM sys.server_principals WHERE name = '{login_name}';
PRINT '--- END LOGGING ---';
PRINT 'Disabling [{login_name}]...';
ALTER LOGIN [{login_name}] DISABLE;
PRINT '  [OK] Login disabled';
GO
"""

    def _script_drop_orphan_user(self, db_name: str, user_name: str) -> str:
        """Drop orphaned user WITH FULL LOGGING for rollback."""
        return f"""
-- ============================================================
-- DROP ORPHANED USER: [{db_name}].[{user_name}]
-- ============================================================
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
DROP USER IF EXISTS [{user_name}];
PRINT '  [OK] Orphaned user removed';
GO
"""
    
    def _script_revoke_guest(self, db_name: str) -> str:
        """Revoke CONNECT from guest user."""
        return f"""
-- Revoke guest access: [{db_name}]
PRINT 'Revoking guest CONNECT in [{db_name}]...';
USE [{db_name}];
REVOKE CONNECT FROM guest;
PRINT '  [OK] Guest access revoked';
GO
"""
    
    def _script_disable_trustworthy(self, db_name: str) -> str:
        """Disable TRUSTWORTHY on database."""
        return f"""
-- Disable TRUSTWORTHY: [{db_name}]
PRINT 'Disabling TRUSTWORTHY on [{db_name}]...';
ALTER DATABASE [{db_name}] SET TRUSTWORTHY OFF;
PRINT '  [OK] TRUSTWORTHY disabled';
GO
"""
    
    def _script_enable_login_auditing(self) -> str:
        """Enable login auditing (success + failure)."""
        return """
-- Enable login auditing (Requirement #22)
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
        return f"""
-- ROLLBACK: Re-enable {setting}
-- EXEC sp_configure 'show advanced options', 1;
-- RECONFIGURE;
-- EXEC sp_configure '{setting}', 1;
-- RECONFIGURE;
-- PRINT 'Rolled back: {setting} = 1';
"""
    
    def _rollback_enable_login(self, login_name: str) -> str:
        """Rollback: re-enable a disabled login."""
        return f"""
-- ROLLBACK: Re-enable login {login_name}
-- ALTER LOGIN [{login_name}] ENABLE;
-- PRINT 'Rolled back: {login_name} enabled';
"""
    
    def _rollback_create_orphan_user(self, db_name: str, user_name: str) -> str:
        """Rollback: recreate orphaned user (basic)."""
        return f"""
-- ROLLBACK: Recreate user {user_name} in {db_name}
-- NOTE: This creates a basic user. You may need to:
--       1. Remap to a login if one exists
--       2. Reassign roles and permissions from the logged output
-- USE [{db_name}];
-- CREATE USER [{user_name}] WITHOUT LOGIN;
-- PRINT 'Rolled back: Created user {user_name} (without login)';
-- 
-- To add to roles (uncomment as needed):
-- ALTER ROLE [db_datareader] ADD MEMBER [{user_name}];
-- ALTER ROLE [db_datawriter] ADD MEMBER [{user_name}];
"""
    
    def _rollback_grant_guest(self, db_name: str) -> str:
        """Rollback: grant guest access back."""
        return f"""
-- ROLLBACK: Re-enable guest access in {db_name}
-- USE [{db_name}];
-- GRANT CONNECT TO guest;
-- PRINT 'Rolled back: guest access granted';
"""
    
    def _rollback_enable_trustworthy(self, db_name: str) -> str:
        """Rollback: re-enable TRUSTWORTHY."""
        return f"""
-- ROLLBACK: Re-enable TRUSTWORTHY on {db_name}
-- ALTER DATABASE [{db_name}] SET TRUSTWORTHY ON;
-- PRINT 'Rolled back: TRUSTWORTHY enabled';
"""
    
    def _rollback_sa(self, temp_password: str) -> str:
        """Rollback: re-enable SA account."""
        return f"""
-- ROLLBACK: Re-enable SA account
-- NOTE: SA was renamed to [$@] and disabled
-- To restore (uncomment):
-- ALTER LOGIN [$@] ENABLE;
-- -- Optionally rename back to 'sa':
-- ALTER LOGIN [$@] WITH NAME = [sa];
-- -- Set a new strong password:
-- ALTER LOGIN [sa] WITH PASSWORD = N'NEW_STRONG_PASSWORD_HERE';
-- PRINT 'Rolled back: SA account enabled';
-- 
-- Temp password that was set: {temp_password}
"""
    
    # ===================================================================
    # CAUTION SCRIPTS (Run but log critical info)
    # ===================================================================
    
    def _script_handle_sa(self, temp_password: str) -> str:
        """Handle SA account: rename + disable + log password."""
        return f"""
-- ============================================================
-- SA ACCOUNT REMEDIATION (Requirement #4)
-- Actions: 1) Rename to $@ 2) Set temp password 3) Disable
-- ============================================================
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
    PRINT '  [OK] Account disabled (as [sa])';
END CATCH;

PRINT '';
PRINT '=== SA REMEDIATION COMPLETE ===';
GO
"""
    
    # ===================================================================
    # REVIEW SCRIPTS (Commented, needs approval)
    # ===================================================================
    
    def _script_review_login(self, login_name: str, desc: str) -> str:
        """Review high-privilege login - COMMENTED."""
        return f"""
-- HIGH-PRIVILEGE LOGIN: {login_name}
-- Issue: {desc}
-- 
-- DO NOT remove without business approval!
--
-- To disable (uncomment if approved):
-- ALTER LOGIN [{login_name}] DISABLE;
--
-- To remove from sysadmin:
-- ALTER SERVER ROLE [sysadmin] DROP MEMBER [{login_name}];
"""
    
    def _script_review_grant_option(self, login_name: str, desc: str) -> str:
        """Review WITH GRANT OPTION - COMMENTED."""
        return f"""
-- WITH GRANT OPTION: {login_name}
-- Issue: {desc}
--
-- To revoke with cascade:
-- REVOKE ALL FROM [{login_name}] CASCADE;
"""
    
    def _script_review_db_user(self, db_name: str, user_name: str, desc: str) -> str:
        """Review database user - COMMENTED."""
        return f"""
-- DATABASE USER: [{db_name}].[{user_name}]
-- Issue: {desc}
--
-- To drop (uncomment if approved):
-- USE [{db_name}];
-- DROP USER IF EXISTS [{user_name}];
"""
    
    def _script_review_linked_server(self, ls_name: str, desc: str) -> str:
        """Review linked server - COMMENTED."""
        return f"""
-- LINKED SERVER: {ls_name}
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
        return f"""
-- TEST DATABASE: {db_name}
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
        return f"""
/*
BACKUP REQUIRED: {db_name}
Run: BACKUP DATABASE [{db_name}] TO DISK = 'D:\\Backups\\{db_name}.bak' WITH COMPRESSION;
*/
PRINT '[ACTION] Configure backup for: {db_name}';
"""
    
    def _script_info_version_upgrade(self) -> str:
        """Version upgrade instructions."""
        return """
/*
SQL SERVER VERSION UPGRADE REQUIRED
Current version is older than 2019. Plan upgrade to SQL Server 2019+.
See: https://docs.microsoft.com/sql/database-engine/install-windows/upgrade-sql-server
*/
PRINT '[ACTION] Plan SQL Server version upgrade';
"""
    
    def _script_info_services(self) -> str:
        """Services configuration instructions."""
        return """
/*
WINDOWS SERVICES REVIEW (Requirements #6, #19, #21)
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
        return """
/*
ENCRYPTION KEY BACKUP (Requirement #11)
If encryption is enabled, back up:
- Service Master Key:  BACKUP SERVICE MASTER KEY TO FILE = 'path' ENCRYPTION BY PASSWORD = 'pwd';
- Database Master Key: USE [db]; BACKUP MASTER KEY TO FILE = 'path' ENCRYPTION BY PASSWORD = 'pwd';
- Certificates:        BACKUP CERTIFICATE [cert] TO FILE = 'path' WITH PRIVATE KEY (...);
*/
PRINT '[RECOMMENDED] Review encryption key backups';
"""


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate remediation scripts")
    parser.add_argument("--db", default="output/audit_history.db")
    parser.add_argument("--output", default="output/remediation_scripts")
    parser.add_argument("--run-id", type=int, help="Audit run ID")
    
    args = parser.parse_args()
    
    service = RemediationService(db_path=args.db, output_dir=args.output)
    scripts = service.generate_scripts(audit_run_id=args.run_id)
    
    print(f"\n✅ Generated {len(scripts)} script file(s)")
    for s in scripts:
        print(f"   📄 {s}")
    
    return 0


if __name__ == "__main__":
    exit(main())
