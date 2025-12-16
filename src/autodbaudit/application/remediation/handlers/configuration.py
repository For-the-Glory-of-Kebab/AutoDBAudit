"""
Remediation handler for Configuration settings (sp_configure).
"""

from __future__ import annotations

from autodbaudit.application.remediation.handlers.base import (
    RemediationHandler,
    RemediationAction,
)


class ConfigurationHandler(RemediationHandler):
    """
    Handles sp_configure remediation.
    """

    def __init__(self, context):
        super().__init__(context)
        self.seen_configs = set()

    def handle(self, finding: dict) -> list[RemediationAction]:
        """
        Generate actions for a finding.
        """
        if finding["finding_type"] != "config":
            return []

        entity = finding["entity_name"]
        if entity in self.seen_configs:
            return []
        self.seen_configs.add(entity)

        script = self._script_disable_config(entity)
        rollback = self._rollback_enable_config(entity)

        return [RemediationAction(script, rollback, "SAFE")]

    def _script_disable_config(self, setting: str) -> str:
        """Disable a dangerous sp_configure setting."""
        header = self._item_header("⚙️ CONFIG", f"Disable {setting}")

        if setting.lower() == "show advanced options":
            prelude = ""
            postlude = ""
        else:
            prelude = """PRINT 'Enabling show advanced options (temporary)...';
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE WITH OVERRIDE;
GO

"""
            postlude = """
PRINT 'Disabling show advanced options (cleanup)...';
EXEC sp_configure 'show advanced options', 0;
RECONFIGURE WITH OVERRIDE;
"""

        return f"""{header}
{prelude}PRINT 'Disabling {setting}...';
EXEC sp_configure '{setting}', 0;
RECONFIGURE WITH OVERRIDE;

-- Verify change (Robustness check)
IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = '{setting}' AND value_in_use = 0)
    PRINT '  [OK] {setting} verified disabled';
ELSE IF EXISTS (SELECT 1 FROM sys.configurations WHERE name = '{setting}' AND value = 0 AND is_dynamic = 0)
    PRINT '  [PENDING RESTART] {setting} set to 0 but requires SQL SERVER RESTART.';
ELSE
    PRINT '  [WARNING] {setting} verification failed. Value_in_use is still 1 (Force failed?).';

{postlude}GO
"""

    def _rollback_enable_config(self, setting: str) -> str:
        """Rollback: Re-enable the config."""
        header = self._item_header("🔙 ROLLBACK", f"Re-enable {setting}")

        if setting.lower() == "show advanced options":
            return f"""{header}
PRINT 'Re-enabling show advanced options...';
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE WITH OVERRIDE;
GO
"""

        return f"""{header}
PRINT 'Enabling show advanced options (temporary)...';
EXEC sp_configure 'show advanced options', 1;
RECONFIGURE WITH OVERRIDE;
GO

PRINT 'Re-enabling {setting}...';
EXEC sp_configure '{setting}', 1;
RECONFIGURE WITH OVERRIDE;
GO

PRINT 'Disabling show advanced options (cleanup)...';
EXEC sp_configure 'show advanced options', 0;
RECONFIGURE WITH OVERRIDE;
"""
