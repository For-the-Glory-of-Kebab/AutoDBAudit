"""
Collector for Database Objects (DBs, Users, Roles, Triggers, Permissions).
"""

from __future__ import annotations

import logging
from autodbaudit.application.collectors.base import BaseCollector
from autodbaudit.application.common.constants import SYSTEM_DBS

logger = logging.getLogger(__name__)


class DatabaseCollector(BaseCollector):
    """
    Collects database-level objects and security settings.
    Orchestrates collection across all databases.
    """

    def collect(self) -> dict[str, int]:
        """
        Collect database objects.
        Returns dict with counts.
        """
        all_dbs, user_dbs = self._collect_databases()

        return {
            "databases": len(all_dbs),
            "db_users": self._collect_db_users(user_dbs),
            "db_roles": self._collect_db_roles(user_dbs),
            "triggers": self._collect_triggers(user_dbs),
            "permissions": self._collect_permissions(user_dbs),
        }

    def _collect_databases(self) -> tuple[list[dict], list[dict]]:
        """Collect databases, returns (all_dbs, user_dbs)."""
        try:
            dbs = self.conn.execute_query(self.prov.get_databases())
            user_dbs = [db for db in dbs if db.get("DatabaseName") not in SYSTEM_DBS]

            for db in dbs:
                db_name = db.get("DatabaseName", "")
                is_trustworthy = bool(db.get("IsTrustworthy"))

                self.writer.add_database(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    database_name=db_name,
                    owner=db.get("Owner", ""),
                    recovery_model=db.get("RecoveryModel", ""),
                    state=db.get("State", ""),
                    data_size_mb=db.get("DataSizeMB") or db.get("SizeMB"),
                    log_size_mb=db.get("LogSizeMB"),
                    is_trustworthy=is_trustworthy,
                )

                # Persist to SQLite (optional)
                if self.ctx.db_conn and self.ctx.instance_id:
                    try:
                        from autodbaudit.infrastructure.sqlite.schema import (
                            save_database,
                        )

                        save_database(
                            connection=self.ctx.db_conn,
                            instance_id=self.ctx.instance_id,
                            audit_run_id=self.ctx.audit_run_id,
                            database_name=db_name,
                            database_id=db.get("DatabaseID"),
                            owner=db.get("Owner", ""),
                            state=db.get("State", ""),
                            recovery_model=db.get("RecoveryModel", ""),
                            is_trustworthy=is_trustworthy,
                            is_encrypted=bool(db.get("IsEncrypted")),
                            size_mb=db.get("DataSizeMB") or db.get("SizeMB"),
                        )
                    except Exception:
                        pass

                # Trustworthy flag is a finding
                if is_trustworthy and db_name not in SYSTEM_DBS:
                    self.save_finding(
                        finding_type="database",
                        entity_name=db_name,
                        status="FAIL",
                        risk_level="high",
                        description=f"Database '{db_name}' has TRUSTWORTHY enabled",
                        recommendation="Disable TRUSTWORTHY unless specifically required",
                    )
            return dbs, user_dbs
        except Exception as e:
            logger.warning("Databases failed: %s", e)
            return [], []

    def _collect_db_users(self, user_dbs: list[dict]) -> int:
        """Collect database users from all user databases."""
        count = 0
        orphan_count = 0
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            if db.get("State", "ONLINE") != "ONLINE":
                continue
            try:
                users = self.conn.execute_query(self.prov.get_database_users(db_name))
                for u in users:
                    user_name = u.get("UserName", "")
                    mapped_login = u.get("MappedLogin")
                    user_type = u.get("UserType", "")

                    is_orphaned = (
                        mapped_login is None
                        and user_type in ("SQL_USER", "WINDOWS_USER")
                        and user_name
                        not in ("dbo", "guest", "INFORMATION_SCHEMA", "sys")
                    )
                    guest_enabled = bool(u.get("GuestEnabled"))

                    self.writer.add_db_user(
                        server_name=self.ctx.server_name,
                        instance_name=self.ctx.instance_name,
                        database_name=db_name,
                        user_name=user_name,
                        user_type=user_type,
                        mapped_login=mapped_login,
                        is_orphaned=is_orphaned,
                        has_connect=(
                            guest_enabled if user_name.lower() == "guest" else True
                        ),
                    )

                    # Persist to SQLite (optional)
                    if self.ctx.db_conn and self.ctx.instance_id:
                        try:
                            from autodbaudit.infrastructure.sqlite.schema import (
                                save_db_user,
                            )

                            save_db_user(
                                connection=self.ctx.db_conn,
                                instance_id=self.ctx.instance_id,
                                audit_run_id=self.ctx.audit_run_id,
                                database_name=db_name,
                                user_name=user_name,
                                login_name=mapped_login,
                                user_type=user_type,
                                is_orphaned=is_orphaned,
                                is_guest=user_name.lower() == "guest",
                                is_guest_enabled=(
                                    guest_enabled
                                    if user_name.lower() == "guest"
                                    else False
                                ),
                            )
                        except Exception:
                            pass

                    count += 1

                    # Orphaned user finding
                    if is_orphaned:
                        orphan_count += 1
                        self.writer.add_orphaned_user(
                            server_name=self.ctx.server_name,
                            instance_name=self.ctx.instance_name,
                            database_name=db_name,
                            user_name=user_name,
                            user_type=user_type,
                        )
                        self.save_finding(
                            finding_type="db_user",
                            entity_name=f"{db_name}|{user_name}",
                            status="WARN",
                            risk_level="medium",
                            description=f"Orphaned user '{user_name}' in database '{db_name}'",
                            recommendation="Remove or remap orphaned user",
                        )

                    # Guest enabled finding
                    if user_name.lower() == "guest" and guest_enabled:
                        self.save_finding(
                            finding_type="db_user",
                            entity_name=f"{db_name}|guest",
                            status="FAIL",
                            risk_level="high",
                            description=f"Guest user enabled in database '{db_name}'",
                            recommendation="Disable guest user access",
                        )
            except Exception:
                pass

        # Add "Not Found" row if no orphaned users were found for this instance
        if orphan_count == 0 and count > 0:
            self.writer.add_orphaned_user_not_found(
                server_name=self.ctx.server_name,
                instance_name=self.ctx.instance_name,
            )

        return count

    def _collect_db_roles(self, user_dbs: list[dict]) -> int:
        """Collect database role memberships."""
        count = 0
        seen_memberships: set[tuple[str, str, str]] = set()

        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            if db.get("State", "ONLINE") != "ONLINE":
                continue
            try:
                roles = self.conn.execute_query(
                    self.prov.get_database_role_members(db_name)
                )

                # Requirement #27: Prepare Role Matrix data
                # Map: member_name -> {"type": str, "roles": set()}
                db_matrix: dict[str, dict] = {}

                for r in roles:
                    role_name = r.get("RoleName", "")
                    member_name = r.get("MemberName", "")
                    member_type = r.get("MemberType", "")

                    # Skip duplicates for list view
                    membership_key = (db_name, role_name, member_name)
                    if membership_key not in seen_memberships:
                        seen_memberships.add(membership_key)
                        self.writer.add_db_role_member(
                            server_name=self.ctx.server_name,
                            instance_name=self.ctx.instance_name,
                            database_name=db_name,
                            role_name=role_name,
                            member_name=member_name,
                            member_type=member_type,
                        )
                        count += 1

                    # Aggregate for Matrix
                    if member_name not in db_matrix:
                        db_matrix[member_name] = {"type": member_type, "roles": set()}
                    db_matrix[member_name]["roles"].add(role_name)

                # Flush Matrix for this database
                for m_name, data in db_matrix.items():
                    self.writer.add_role_matrix_row(
                        server_name=self.ctx.server_name,
                        instance_name=self.ctx.instance_name,
                        database_name=db_name,
                        principal_name=m_name,
                        principal_type=data["type"],
                        roles=list(data["roles"]),
                    )

            except Exception:
                pass
        return count

    def _collect_triggers(self, user_dbs: list[dict]) -> int:
        """Collect database and server triggers."""
        count = 0

        # 1. Server Triggers
        try:
            srv_triggers = self.conn.execute_query(self.prov.get_server_triggers())
            for t in srv_triggers:
                self.writer.add_trigger(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    level="SERVER",
                    database_name="(Server)",
                    trigger_name=t.get("TriggerName", ""),
                    event_type=t.get("EventType", ""),
                    is_enabled=not bool(t.get("IsDisabled")),
                )
                count += 1
        except Exception as e:
            logger.warning("Server triggers failed: %s", e)

        # 2. Database Triggers
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            if db.get("State", "ONLINE") != "ONLINE":
                continue
            try:
                triggers = self.conn.execute_query(
                    self.prov.get_database_triggers(db_name)
                )
                for t in triggers:
                    self.writer.add_trigger(
                        server_name=self.ctx.server_name,
                        instance_name=self.ctx.instance_name,
                        database_name=db_name,
                        trigger_name=t.get("TriggerName", ""),
                        event_type=t.get("TriggerType", ""),
                        is_enabled=not bool(t.get("IsDisabled")),
                        level="DATABASE",
                    )
                    count += 1
            except Exception:
                pass
        return count

    def _collect_permissions(self, user_dbs: list[dict]) -> int:
        """Collect database and server permissions."""
        count = 0

        # 1. Server Permissions
        try:
            srv_perms = self.conn.execute_query(self.prov.get_server_permissions())
            for p in srv_perms:
                self.writer.add_permission(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    scope="SERVER",
                    database_name="(Server)",
                    grantee_name=p.get("GranteeName", ""),
                    permission_name=p.get("PermissionName", ""),
                    state=p.get("PermissionState", ""),
                    entity_name=p.get("EntityName", ""),
                    class_desc=p.get("PermissionClass", ""),
                )
                count += 1
        except Exception as e:
            logger.warning("Server permissions failed: %s", e)

        # 2. Database Permissions
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            if db.get("State", "ONLINE") != "ONLINE":
                continue
            try:
                perms = self.conn.execute_query(
                    self.prov.get_database_permissions(db_name)
                )
                for p in perms:
                    self.writer.add_permission(
                        server_name=self.ctx.server_name,
                        instance_name=self.ctx.instance_name,
                        scope="DATABASE",
                        database_name=db_name,
                        grantee_name=p.get("GranteeName", ""),
                        permission_name=p.get("PermissionName", ""),
                        state=p.get("PermissionState", ""),
                        entity_name=p.get("EntityName", ""),
                        class_desc=p.get("PermissionClass", ""),
                    )
                    count += 1
            except Exception:
                pass
        return count
