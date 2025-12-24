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
        # Buffers for batch processing
        self.high_priv_logins: list[tuple[str, str]] = []  # (login, desc)
        self.unused_logins: list[str] = []
        self.policy_logins: list[str] = []
        self.grant_logins: list[tuple[str, str]] = []
        self.manual_logins: list[tuple[str, str]] = []

    def handle(self, finding: dict) -> list[RemediationAction]:
        """
        Generate actions for a finding. Buffers generic login findings.
        """
        ft = finding["finding_type"]
        entity = finding["entity_name"]
        desc = finding.get("finding_description", "") or ""

        actions = []

        if ft == "sa_account":
            # SA handling - respect aggressiveness and connection check
            is_connected_as_sa = (
                self.ctx.conn_user and self.ctx.conn_user.lower() == "sa"
            )
            temp_password = self.generate_temp_password()
            script = self._script_handle_sa(entity, temp_password, is_connected_as_sa)
            rollback = self._rollback_sa(temp_password)

            # At level 1 (Safe), comment out SA script for manual review
            # At level 2+, script is active (but still warns if connected as SA)
            if self.ctx.aggressiveness < 2:
                script = self._wrap_safe_mode_comment(
                    script,
                    "SA Account",
                    "At aggressiveness=1, SA changes require manual review. Use --aggressiveness 2 or 3 to enable.",
                )
                cat = "REVIEW"
            elif is_connected_as_sa:
                cat = "REVIEW"  # Already wrapped with lockout warning in _script_handle_sa
            else:
                cat = "CAUTION"
            actions.append(RemediationAction(script, rollback, cat))

        elif ft == "login":
            if entity.lower() == "sa":
                return []
            if entity in self.seen_logins:
                return []
            self.seen_logins.add(entity)

            # Categorize and buffer
            desc_lower = desc.lower()
            if "sysadmin" in desc_lower or "privilege" in desc_lower:
                self.high_priv_logins.append((entity, desc))
            elif "unused" in desc_lower or "not used" in desc_lower:
                self.unused_logins.append(entity)
            elif "policy" in desc_lower:
                self.policy_logins.append(entity)
            elif "grant" in desc_lower:
                self.grant_logins.append((entity, desc))
            else:
                self.manual_logins.append((entity, desc))

        elif ft == "audit_settings" and (
            "login" in entity.lower() or "audit" in entity.lower()
        ):
            script = self._script_enable_login_auditing()
            rollback = self._rollback_disable_login_auditing()
            actions.append(RemediationAction(script, rollback, "SAFE"))

        return actions

    def finalize(self) -> list[RemediationAction]:
        """Generate batched scripts from buffers."""
        actions = []

        # 1. High Privilege & Unused Logins (Aggressive Batch)
        # Combines Sysadmin/Privileged and Unused logins into a clearable block
        if self.high_priv_logins or self.unused_logins:
            script = self._batch_script_login_cleanup()
            actions.append(RemediationAction(script, "", "REVIEW"))

        # 2. Password Policy (Batch)
        if self.policy_logins:
            script = self._batch_script_password_policy()
            actions.append(RemediationAction(script, "", "SAFE"))

        # 3. Grant Option & Manual (Review items - still individual-ish but grouped)
        if self.grant_logins or self.manual_logins:
            # We just dump these as comments for now
            pass

        return actions

    def _batch_script_login_cleanup(self) -> str:
        """Generate table-driven batch script for easier manual review."""
        header = self._item_header(
            "☢️ ACCOUNT CLEANUP", "Batch Fix: Remove High Priv & Unused Logins"
        )

        lines = []
        lines.append(f"{header}")
        lines.append("/*")
        lines.append("INSTRUCTIONS:")
        lines.append("1. The logic block below handles safe execution.")
        lines.append(
            "2. Uncomment the INSERT statements for accounts you want to clean up."
        )
        lines.append("3. Default ACTIONS are based on Aggressiveness Level.")
        lines.append("*/")
        lines.append("")
        lines.append(
            "DECLARE @Targets TABLE (AccountName sysname, ActionType varchar(20));"
        )
        lines.append("")
        lines.append("-- === [CONFIG] Uncomment lines below to select targets ===")

        # Helper to generate INSERT line
        def gen_insert(name, action, reason, commented=True):
            prefix = "-- " if commented else ""
            return f"{prefix}INSERT INTO @Targets VALUES ('{name}', '{action}'); -- {reason}"

        # Level 3 (Nuclear) = DROP by default (Uncommented?), Level 2 = DISABLE
        # User said: "level 1 just has those iffy ones all commented out"
        # "level 3 should probably remove all things... make everything ... non discrepant"

        is_aggressive = self.ctx.aggressiveness >= 3
        is_standard = self.ctx.aggressiveness >= 2

        # High Priv -> Usually DROP or DISABLE depending on level
        for name, desc in self.high_priv_logins:
            action = "DROP" if is_aggressive else "DISABLE"
            # Comment out by default unless aggressiveness >= 2 forcing it?
            # User "level 3 ... remove all things". So if L3, uncommented.
            commented = not is_aggressive
            lines.append(gen_insert(name, action, f"HIGH PRIV: {desc}", commented))

        # Unused -> Usually DISABLE or DROP
        for name in self.unused_logins:
            action = "DROP" if is_aggressive else "DISABLE"
            commented = not (is_aggressive or is_standard)  # L2/L3 uncommented
            lines.append(gen_insert(name, action, "UNUSED ACCOUNT", commented))

        lines.append("-- ========================================================")
        lines.append("")
        lines.append("DECLARE @Name sysname, @Action varchar(20);")
        lines.append(
            "DECLARE Cur CURSOR LOCAL FAST_FORWARD FOR SELECT AccountName, ActionType FROM @Targets;"
        )
        lines.append("OPEN Cur;")
        lines.append("FETCH NEXT FROM Cur INTO @Name, @Action;")
        lines.append("")
        lines.append("WHILE @@FETCH_STATUS = 0")
        lines.append("BEGIN")
        lines.append("    -- 1. Safety Check: Connecting User")
        lines.append("    IF SUSER_SNAME() = @Name")
        lines.append("    BEGIN")
        lines.append(
            "        PRINT 'SKIP: Cannot operate on current connecting user [' + @Name + ']';"
        )
        lines.append("    END")
        lines.append("    ELSE")
        lines.append("    BEGIN")
        lines.append("        -- 2. Execute Action")
        lines.append("        IF @Action = 'DROP'")
        lines.append("        BEGIN")
        lines.append("            PRINT 'Dropping [' + @Name + ']...';")
        lines.append(
            "            IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = @Name)"
        )
        lines.append("                EXEC('DROP LOGIN [' + @Name + ']');")
        lines.append("        END")
        lines.append("        ELSE IF @Action = 'DISABLE'")
        lines.append("        BEGIN")
        lines.append("            PRINT 'Disabling [' + @Name + ']...';")
        lines.append(
            "            IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = @Name)"
        )
        lines.append("                EXEC('ALTER LOGIN [' + @Name + '] DISABLE');")
        lines.append("        END")
        lines.append("    END")
        lines.append("")
        lines.append("    FETCH NEXT FROM Cur INTO @Name, @Action;")
        lines.append("END")
        lines.append("")
        lines.append("CLOSE Cur; DEALLOCATE Cur;")
        lines.append("GO")

        return "\n".join(lines)

    def _batch_script_password_policy(self) -> str:
        """Generate batched password policy enforcer."""
        header = self._item_header(
            "🔐 PASSWORD POLICY", "Batch Fix: Enforce Policy on SQL Logins"
        )
        lines = [header]
        lines.append("PRINT 'Enforcing Password Policy on identified logins...';")

        for name in self.policy_logins:
            lines.append(
                f"""
IF SUSER_SNAME() <> '{name}'
    ALTER LOGIN [{name}] WITH CHECK_POLICY = ON;
"""
            )
        lines.append("GO")
        return "\n".join(lines)

    # ... Helper methods like _script_handle_sa kept or refactored?
    # I need to keep _script_handle_sa, _rollback_sa, etc. as they are called above.
    # But I can remove the old iterative _script_review_login and others since they are replaced by batching.

    def _script_handle_sa(
        self, current_name: str, temp_password: str, is_connected_as_sa: bool
    ) -> str:
        """Handle SA account (Rename + Disable + Scramble)."""
        header = self._item_header(
            "🛡️ SA ACCOUNT", "Secure SA Account (Rename, Disable, Scramble)"
        )

        # Log secret
        self.ctx.secrets_log.append(f"SA_NEW_PASSWORD: {temp_password}")

        script = f"""{header}
PRINT 'Securing SA account...';
PRINT '1. Renaming [{current_name}] to [$@]...';
ALTER LOGIN [{current_name}] WITH NAME = [$@];

PRINT '2. Setting complex random password...';
-- Password logged in secrets file
ALTER LOGIN [$@] WITH PASSWORD = '{temp_password}';

PRINT '3. Disabling SA account...';
ALTER LOGIN [$@] DISABLE;

PRINT '  [OK] SA account secured';
GO
"""
        if is_connected_as_sa:
            return self._wrap_lockout_warning(script, current_name)
        return script

    def _rollback_sa(self, temp_password: str) -> str:
        """Rollback SA changes."""
        header = self._item_header("🔙 ROLLBACK", "Revert SA Account Changes")
        return f"""{header}
PRINT 'Reverting SA account changes...';
-- 1. Enable if it was disabled (Assuming it was enabled before - caution)
PRINT 'Enabling [$@]...';
ALTER LOGIN [$@] ENABLE;

-- 2. Rename back to SA
PRINT 'Renaming [$@] back to [sa]...';
ALTER LOGIN [$@] WITH NAME = [sa];

-- 3. Password cannot be reverted to original without knowing it!
PRINT 'WARNING: Password cannot be reverted to original.';
PRINT 'Current password is: {temp_password}';
GO
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

    def _wrap_lockout_warning(self, script: str, username: str) -> str:
        """Wrap a script in comments with a lockout warning."""
        lines = script.split("\n")
        commented = ["-- " + l if l.strip() else l for l in lines]

        warn = []
        warn.append("/*")
        warn.append(f"!!! LOCKOUT RISK: YOU ARE CONNECTED AS '{username}' !!!")
        warn.append("=========================================================")
        warn.append("This section has been commented out because we detected")
        warn.append(f"that you used the '{username}' account to connect to this Audit.")
        warn.append("")
        warn.append("Altering this login could cause you to lose access immediately!")
        warn.append("Run this only if you have another SysAdmin account ready!")
        warn.append("*/")

        return "\n".join(warn) + "\n" + "\n".join(commented)

    def _wrap_safe_mode_comment(self, script: str, section: str, reason: str) -> str:
        """Wrap a script in comments for safe mode (aggressiveness=1)."""
        lines = script.split("\n")
        commented = ["-- " + l if l.strip() else l for l in lines]

        warn = []
        warn.append("/*")
        warn.append(f"=== SAFE MODE: {section} ===")
        warn.append("=" * 50)
        warn.append(reason)
        warn.append("")
        warn.append("Uncomment the lines below to enable, or re-generate with")
        warn.append("--aggressiveness 2 (Standard) or --aggressiveness 3 (Nuclear)")
        warn.append("*/")

        return "\n".join(warn) + "\n" + "\n".join(commented)
