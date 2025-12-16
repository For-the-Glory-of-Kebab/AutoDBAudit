"""
Remediation handler for Infrastructure properties, Linked Servers, Backups, and Info.
"""

from __future__ import annotations

from autodbaudit.application.remediation.handlers.base import (
    RemediationHandler,
    RemediationAction,
)


class InfrastructureHandler(RemediationHandler):
    """
    Handles Linked Servers, Backups, Version Info, Encryption Info.
    """

    def handle(self, finding: dict) -> list[RemediationAction]:
        """Generate actions."""
        ft = finding["finding_type"]
        entity = finding["entity_name"]
        desc = finding.get("finding_description", "") or ""

        actions = []

        if ft == "linked_server":
            # Always REVIEW
            script = self._script_review_linked_server(entity, desc)
            actions.append(RemediationAction(script, "-- Manual action", "REVIEW"))

        elif ft == "backup":
            # Always INFO
            script = self._script_info_backup(entity)
            actions.append(RemediationAction(script, "", "INFO"))

        elif ft == "version":
            # Always INFO
            script = self._script_info_version_upgrade()
            actions.append(RemediationAction(script, "", "INFO"))

        elif ft == "encryption":
            # Always INFO (detected via info_section logic in old service, but here triggered by finding)
            # Wait, logic in old service: if has_encryption_finding -> info.
            # Actually, old logic: `info_section.append(self._script_info_encryption())` was ALWAYS added at end.
            # We should probably handle that in the Service or here if finding exists.
            # Ideally, we add a single INFO script for all encryption findings.
            pass

        return actions

    def get_global_info_scripts(self) -> list[RemediationAction]:
        """Return scripts that should always be included (like encryption info)."""
        # This mirrors the unconditional `info_section.append(self._script_info_encryption())`
        return [RemediationAction(self._script_info_encryption(), "", "INFO")]

    def _script_review_linked_server(self, server_name: str, desc: str) -> str:
        header = self._item_header("👀 REVIEW", f"Linked Server: {server_name}")
        return f"""{header}
/*
ISSUE: {desc}
Linked Server: {server_name}

RECOMMENDATION: Review RPC configuration and necessity.
*/
-- EXEC master.dbo.sp_dropserver @server=N'{server_name}', @droplogins='droplogins';
"""

    def _script_info_backup(self, entity: str) -> str:
        header = self._item_header("ℹ️ INFO", f"Backup Issue: {entity}")
        return f"""{header}
/*
ISSUE: Missing backups detected for {entity.replace('|', ' -> ')}.
action:
1. Check SQL Server Agent jobs.
2. Verify Maintenance Plans.
3. Ensure Transaction Log backups are running for FULL recovery model.
*/
"""

    def _script_info_version_upgrade(self) -> str:
        header = self._item_header("ℹ️ UPDATE", "SQL Server Version Update Available")
        return f"""{header}
/*
ISSUE: SQL Server version is older than the expected baseline.
RECOMMENDATION: Plan an upgrade to the latest Service Pack and Cumulative Update.

Resources:
- https://sqlserverbuilds.blogspot.com/
- https://learn.microsoft.com/en-us/sql/database-engine/install-windows/latest-updates-for-microsoft-sql-server
*/
"""

    def _script_info_encryption(self) -> str:
        header = self._item_header("ℹ️ INFO", "Encryption Status")
        return f"""{header}
/*
Encryption Hierarchy:
- Verify Service Master Key (SMK) is backed up.
- Verify Database Master Keys (DMK) are backed up.
- Rotate Certificates periodically.

To view keys:
SELECT db_name(database_id), * FROM sys.dm_database_encryption_keys;
*/
"""
