"""
Remediation handler for Database objects (Users, Properties).
"""

from __future__ import annotations

from autodbaudit.application.remediation.handlers.base import (
    RemediationHandler,
    RemediationAction,
)


class DatabaseHandler(RemediationHandler):
    """
    Handles Database Users and Properties.
    """

    def __init__(self, context):
        super().__init__(context)
        self.seen_db_users = set()

    def handle(self, finding: dict) -> list[RemediationAction]:
        """Generate actions for database findings."""
        ft = finding["finding_type"]
        entity = finding["entity_name"]
        desc = finding.get("finding_description", "") or ""

        actions = []

        if ft == "db_user":
            key = entity
            if key in self.seen_db_users:
                return []
            self.seen_db_users.add(key)

            if "|" in entity:
                db_name, user_name = entity.split("|", 1)
            else:
                db_name, user_name = "master", entity

            if "orphan" in desc.lower():
                # Orphaned user -> SAFE (Auto-fix)
                script = self._script_drop_orphan_user(db_name, user_name)
                rollback = self._rollback_create_orphan_user(db_name, user_name)
                actions.append(RemediationAction(script, rollback, "SAFE"))

            elif "guest" in desc.lower() or user_name.lower() == "guest":
                # Guest user -> SAFE
                script = self._script_revoke_guest(db_name)
                rollback = self._rollback_grant_guest(db_name)
                actions.append(RemediationAction(script, rollback, "SAFE"))

            else:
                # Other db users -> REVIEW
                script = self._script_review_db_user(db_name, user_name, desc)
                actions.append(RemediationAction(script, "-- Manual action", "REVIEW"))

        elif ft == "database":
            db_name = entity
            if "trustworthy" in desc.lower():
                script = self._script_disable_trustworthy(db_name)
                rollback = self._rollback_enable_trustworthy(db_name)
                actions.append(RemediationAction(script, rollback, "SAFE"))
            elif any(
                x in db_name.lower()
                for x in ["adventureworks", "pubs", "northwind", "test"]
            ):
                script = self._script_review_test_database(db_name)
                actions.append(RemediationAction(script, "-- Manual action", "REVIEW"))

        return actions

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

    def _rollback_create_orphan_user(self, db_name: str, user_name: str) -> str:
        header = self._item_header(
            "🔙 ROLLBACK", f"Re-create orphan user: [{db_name}].[{user_name}]"
        )
        return f"""{header}
PRINT 'Re-creating user [{user_name}] in [{db_name}]...';
USE [{db_name}];
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = '{user_name}')
BEGIN
    CREATE USER [{user_name}] WITHOUT LOGIN;
    PRINT '  [OK] User created (WITHOUT LOGIN)';
    PRINT '  NOTE: Permissions and Role memberships must be restored manually from logs!';
END
GO
"""

    def _script_revoke_guest(self, db_name: str) -> str:
        header = self._item_header("👤 GUEST", f"Revoke guest access: [{db_name}]")
        return f"""{header}
PRINT 'Revoking guest CONNECT in [{db_name}]...';
USE [{db_name}];
REVOKE CONNECT FROM guest;
PRINT '  [OK] Guest access revoked';
GO
"""

    def _rollback_grant_guest(self, db_name: str) -> str:
        header = self._item_header("🔙 ROLLBACK", f"Grant guest access: [{db_name}]")
        return f"""{header}
PRINT 'Granting guest CONNECT in [{db_name}]...';
USE [{db_name}];
GRANT CONNECT TO guest;
PRINT '  [OK] Guest access granted';
GO
"""

    def _script_disable_trustworthy(self, db_name: str) -> str:
        header = self._item_header("🛢️ DATABASE", f"Disable TRUSTWORTHY: [{db_name}]")
        return f"""{header}
PRINT 'Disabling TRUSTWORTHY on [{db_name}]...';
ALTER DATABASE [{db_name}] SET TRUSTWORTHY OFF;
PRINT '  [OK] TRUSTWORTHY disabled';
GO
"""

    def _rollback_enable_trustworthy(self, db_name: str) -> str:
        header = self._item_header("🔙 ROLLBACK", f"Enable TRUSTWORTHY: [{db_name}]")
        return f"""{header}
PRINT 'Enabling TRUSTWORTHY on [{db_name}]...';
ALTER DATABASE [{db_name}] SET TRUSTWORTHY ON;
PRINT '  [OK] TRUSTWORTHY enabled';
GO
"""

    def _script_review_db_user(self, db_name: str, user_name: str, desc: str) -> str:
        header = self._item_header(
            "👀 REVIEW", f"Database User: [{db_name}].[{user_name}]"
        )
        return f"""{header}
/*
ISSUE: {desc}
User: {user_name}
Database: {db_name}

RECOMMENDATION: Review why this user exists and has permissions.
*/
-- USE [{db_name}];
-- DROP USER [{user_name}];
"""

    def _script_review_test_database(self, db_name: str) -> str:
        header = self._item_header("👀 REVIEW", f"Test Database: {db_name}")
        return f"""{header}
/*
ISSUE: Potential test/sample database detected.
Database: {db_name}

RECOMMENDATION: Remove from production environment if not needed.
*/
-- DROP DATABASE [{db_name}];
"""
