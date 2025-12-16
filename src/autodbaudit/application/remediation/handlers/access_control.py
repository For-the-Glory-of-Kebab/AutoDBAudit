"""
Remediation handler for Access Control (Logins, SA).
"""

from __future__ import annotations

from autodbaudit.application.remediation.handlers.base import (
    RemediationHandler,
    RemediationAction,
)


class AccessControlHandler(RemediationHandler):
    """
    Handles Logins and SA Account remediation.
    """

    def __init__(self, context):
        super().__init__(context)
        self.seen_logins = set()

    def handle(self, finding: dict) -> list[RemediationAction]:
        """
        Generate actions for a finding.
        """
        ft = finding["finding_type"]
        entity = finding["entity_name"]
        desc = finding.get("finding_description", "") or ""

        actions = []

        if ft == "sa_account":
            # SA handling is special, usually done once per instance.
            # We'll just generate it here based on the finding.
            # Check if we are connected as SA
            is_connected_as_sa = (
                self.ctx.conn_user and self.ctx.conn_user.lower() == "sa"
            )

            # Generate temp password
            temp_password = self.generate_temp_password()

            script = self._script_handle_sa(temp_password, is_connected_as_sa)
            rollback = self._rollback_sa(temp_password)

            cat = "REVIEW" if is_connected_as_sa else "CAUTION"
            actions.append(RemediationAction(script, rollback, cat))

        elif ft == "login":
            if entity.lower() == "sa":
                return []  # Handled by sa_account or duplicates

            if entity in self.seen_logins:
                return []
            self.seen_logins.add(entity)

            is_connected_user = bool(
                self.ctx.conn_user
                and entity.strip().lower() == self.ctx.conn_user.strip().lower()
            )

            if "sysadmin" in desc.lower() or "privilege" in desc.lower():
                # High priv -> REVIEW
                script = self._script_review_login(
                    entity, desc, is_connected_user, self.ctx.aggressiveness
                )
                actions.append(
                    RemediationAction(
                        script, "-- No rollback for review items", "REVIEW"
                    )
                )

            elif "unused" in desc.lower() or "not used" in desc.lower():
                # Unused -> SAFE (unless connected user)
                script = self._script_disable_unused_login(entity, is_connected_user)
                rollback = self._rollback_enable_login(entity)
                cat = "REVIEW" if is_connected_user else "SAFE"
                actions.append(RemediationAction(script, rollback, cat))

            elif "policy" in desc.lower():
                # Password Policy -> SAFE
                script = self._script_enable_password_policy(entity, is_connected_user)
                rollback = "-- Cannot revert password policy cleanly without knowing previous state"
                cat = "REVIEW" if is_connected_user else "SAFE"
                actions.append(RemediationAction(script, rollback, cat))

            elif "grant" in desc.lower():
                # Grant option -> REVIEW
                script = self._script_review_grant_option(entity, desc)
                actions.append(RemediationAction(script, "-- Manual action", "REVIEW"))

            else:
                # Default -> REVIEW
                script = self._script_review_login(
                    entity, desc, is_connected_user, self.ctx.aggressiveness
                )
                actions.append(RemediationAction(script, "-- Manual action", "REVIEW"))

        elif ft == "audit_settings" and (
            "login" in entity.lower() or "audit" in entity.lower()
        ):
            # Login Auditing
            script = self._script_enable_login_auditing()
            rollback = self._rollback_disable_login_auditing()
            actions.append(RemediationAction(script, rollback, "SAFE"))

        return actions

    def _script_handle_sa(self, temp_password: str, is_connected_as_sa: bool) -> str:
        """Handle SA account (Rename + Disable + Scramble)."""
        header = self._item_header(
            "🛡️ SA ACCOUNT", "Secure SA Account (Rename, Disable, Scramble)"
        )

        # Log secret
        self.ctx.secrets_log.append(f"SA_NEW_PASSWORD: {temp_password}")

        script = f"""{header}
PRINT 'Securing SA account...';
PRINT '1. Renaming SA to [x_sa_renamed]...';
ALTER LOGIN [sa] WITH NAME = [x_sa_renamed];

PRINT '2. Setting complex random password...';
-- Password logged in secrets file
ALTER LOGIN [x_sa_renamed] WITH PASSWORD = '{temp_password}';

PRINT '3. Disabling SA account...';
ALTER LOGIN [x_sa_renamed] DISABLE;

PRINT '  [OK] SA account secured';
GO
"""
        if is_connected_as_sa:
            return self._wrap_lockout_warning(script, "sa")
        return script

    def _rollback_sa(self, temp_password: str) -> str:
        """Rollback SA changes."""
        header = self._item_header("🔙 ROLLBACK", "Revert SA Account Changes")
        return f"""{header}
PRINT 'Reverting SA account changes...';
-- 1. Enable if it was disabled (Assuming it was enabled before - caution)
PRINT 'Enabling [x_sa_renamed]...';
ALTER LOGIN [x_sa_renamed] ENABLE;

-- 2. Rename back to SA
PRINT 'Renaming [x_sa_renamed] back to [sa]...';
ALTER LOGIN [x_sa_renamed] WITH NAME = [sa];

-- 3. Password cannot be reverted to original without knowing it!
PRINT 'WARNING: Password cannot be reverted to original.';
PRINT 'Current password is: {temp_password}';
GO
"""

    def _script_review_login(
        self, entity: str, desc: str, is_connected_user: bool, aggressiveness: int
    ) -> str:
        """Generate review script for generic login findings."""
        header = self._item_header("👀 MANUAL REVIEW", f"Login Issue: {entity}")
        script = f"""{header}
/*
ISSUE: {desc}
Login: [{entity}]

RECOMMENDATION: Review permissions and disable if not needed.
*/

-- EXEC sp_revokedbaccess '{entity}';
-- EXEC sp_droplogin '{entity}';
"""
        return script

    def _script_disable_unused_login(
        self, login_name: str, is_connected_user: bool
    ) -> str:
        # Same logic as original
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

    def _rollback_enable_login(self, login_name: str) -> str:
        header = self._item_header("🔙 ROLLBACK", f"Enable login: {login_name}")
        return f"""{header}
PRINT 'Re-enabling [{login_name}]...';
ALTER LOGIN [{login_name}] ENABLE;
PRINT '  [OK] Login enabled';
GO
"""

    def _script_enable_password_policy(
        self, login_name: str, is_connected_user: bool
    ) -> str:
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

    def _script_review_grant_option(self, entity: str, desc: str) -> str:
        header = self._item_header("👀 REVIEW", f"WITH GRANT OPTION: {entity}")
        return f"""{header}
/*
ISSUE: {desc}
Login [{entity}] has ability to grant permissions to others.
Review and revoke if not necessary.
*/
-- REVOKE GRANT OPTION FOR ... FROM [{entity}];
"""

    def _script_enable_login_auditing(self) -> str:
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
    3; -- 3 = Both failed and successful logins
PRINT '  [OK] Login auditing enabled (Pending Restart)';
GO
"""

    def _rollback_disable_login_auditing(self) -> str:
        header = self._item_header("🔙 ROLLBACK", "Revert login auditing")
        return f"""{header}
PRINT 'Setting login auditing to None (0) or Failed Only (2)...';
-- Defaulting to Failed Only (2) as safe fallback
EXEC xp_instance_regwrite 
    N'HKEY_LOCAL_MACHINE', 
    N'Software\\Microsoft\\MSSQLServer\\MSSQLServer', 
    N'AuditLevel', 
    REG_DWORD, 
    2;
GO
"""
