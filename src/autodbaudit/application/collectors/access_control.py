"""
Collector for Access Control (Logins, Roles, SA Account).
"""

from __future__ import annotations

import logging
from autodbaudit.application.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class AccessControlCollector(BaseCollector):
    """
    Collects and audits server-level access control:
    - Logins
    - Server Roles
    - SA Account status
    """

    def collect(self) -> dict[str, int]:
        """
        Collect access control data.
        Returns dict with counts: {'sa': int, 'logins': int, 'roles': int}
        """
        logins = self._get_logins()

        count_sa = self._collect_sa_account(logins)
        count_logins = self._collect_logins(logins)
        count_roles = self._collect_roles()

        return {"sa": count_sa, "logins": count_logins, "roles": count_roles}

    def _get_logins(self) -> list[dict]:
        """Get server logins."""
        return self.conn.execute_query(self.prov.get_server_logins())

    def _collect_sa_account(self, logins: list[dict]) -> int:
        """Collect SA account status."""
        for lg in logins:
            if bool(lg.get("IsSA")):
                login_name = lg.get("LoginName", "")
                is_disabled = bool(lg.get("IsDisabled"))
                is_renamed = login_name.lower() != "sa"

                self.writer.add_sa_account(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    is_disabled=is_disabled,
                    is_renamed=is_renamed,
                    current_name=login_name,
                    default_db=lg.get("DefaultDatabase", "master"),
                )

                # Save finding to SQLite
                if is_disabled:
                    status = "PASS"
                    desc = "SA account is disabled"
                else:
                    status = "FAIL"
                    desc = "SA account is enabled"

                self.save_finding(
                    finding_type="sa_account",
                    entity_name=login_name,
                    status=status,
                    risk_level="critical" if not is_disabled else None,
                    description=desc,
                    recommendation="Disable SA account" if not is_disabled else None,
                )
                return 1
        return 0

    def _collect_logins(self, logins: list[dict]) -> int:
        """Collect server logins."""
        for lg in logins:
            login_name = lg.get("LoginName", "")
            login_type = lg.get("LoginType", "")
            is_disabled = bool(lg.get("IsDisabled"))
            pwd_policy = lg.get("PasswordPolicyEnforced")

            logger.warning(
                f"DEBUG: Login={login_name}, Type={login_type}, Disabled={is_disabled}, Policy={pwd_policy}"
            )

            self.writer.add_login(
                server_name=self.ctx.server_name,
                instance_name=self.ctx.instance_name,
                login_name=login_name,
                login_type=login_type,
                is_disabled=is_disabled,
                pwd_policy=pwd_policy,
                default_db=lg.get("DefaultDatabase", ""),
            )

            # Persist to SQLite (optional)
            if self.ctx.db_conn and self.ctx.instance_id:
                try:
                    from autodbaudit.infrastructure.sqlite.schema import save_login

                    save_login(
                        connection=self.ctx.db_conn,
                        instance_id=self.ctx.instance_id,
                        audit_run_id=self.ctx.audit_run_id,
                        login_name=login_name,
                        login_type=login_type,
                        is_disabled=is_disabled,
                        password_policy=pwd_policy,
                        default_database=lg.get("DefaultDatabase", ""),
                        is_sa=bool(lg.get("IsSA")),
                        create_date=(
                            str(lg.get("CreateDate", ""))
                            if lg.get("CreateDate")
                            else None
                        ),
                    )
                except Exception:
                    pass

            # SQL logins (not Windows auth) are findings
            if login_type == "SQL_LOGIN" and not is_disabled:
                self.save_finding(
                    finding_type="login",
                    entity_name=login_name,
                    status="WARN",
                    risk_level="medium",
                    description=f"SQL login '{login_name}' (not Windows auth)",
                    recommendation="Consider Windows authentication where possible",
                )
            # Disabled logins with policy issues
            elif not pwd_policy and login_type == "SQL_LOGIN":
                self.save_finding(
                    finding_type="login",
                    entity_name=login_name,
                    status="FAIL",
                    risk_level="high",
                    description=f"SQL login '{login_name}' without password policy",
                    recommendation="Enable password policy enforcement",
                )
        return len(logins)

    def _collect_roles(self) -> int:
        """Collect server role memberships."""
        try:
            roles = self.conn.execute_query(self.prov.get_server_role_members())
            for r in roles:
                self.writer.add_role_member(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    role_name=r.get("RoleName", ""),
                    member_name=r.get("MemberName", ""),
                    member_type=r.get("MemberType", ""),
                    is_disabled=bool(r.get("MemberDisabled")),
                )

                # Save finding for ALL role members to ensure stats counting works
                # "Results-Based Persistence": Findings table drives compliance
                role_name = r.get("RoleName", "")
                member_name = r.get("MemberName", "")
                
                # Determine status based on role sensitivity
                status = "PASS"
                risk_level = None
                desc = f"Member of '{role_name}': {member_name}"
                rec = None
                
                if role_name == "sysadmin":
                    status = "FAIL"
                    risk_level = "critical"
                    rec = "Review sysadmin membership"
                elif role_name in ("securityadmin", "serveradmin"):
                    status = "WARN"
                    risk_level = "high"
                    rec = f"Review {role_name} membership"

                # Entity key must be unique per role assignment (Role|Member)
                # Matches SHEET_ANNOTATION_CONFIG key structure
                entity_key = f"{role_name}|{member_name}"

                self.save_finding(
                    finding_type="server_role_member",
                    entity_name=member_name,
                    status=status,
                    risk_level=risk_level,
                    description=desc,
                    recommendation=rec,
                    entity_key=entity_key,
                )
            return len(roles)
        except Exception as e:
            logger.warning("Roles failed: %s", e)
            return 0
