"""
Audit Data Collector.

Collects all security audit data from a SQL Server instance and
populates an ExcelReportWriter. This class extracts the data collection
logic from test_multi_instance.py into a reusable component.

Usage:
    collector = AuditDataCollector(connector, query_provider, writer)
    collector.collect_all(server_name, instance_name)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.infrastructure.sql.connector import SqlConnector
    from autodbaudit.infrastructure.sql.query_provider import QueryProvider
    from autodbaudit.infrastructure.excel import EnhancedReportWriter

logger = logging.getLogger(__name__)


# Security settings to audit (per db-requirements.md)
SECURITY_SETTINGS = {
    # HIGH RISK - command execution
    "xp_cmdshell": (0, "high"),
    "Ole Automation Procedures": (0, "high"),
    # MEDIUM RISK - feature surface area
    "clr enabled": (0, "medium"),
    "clr strict security": (1, "medium"),
    "Ad Hoc Distributed Queries": (0, "medium"),
    "Database Mail XPs": (0, "medium"),
    "cross db ownership chaining": (0, "medium"),
    "remote access": (0, "medium"),
    "remote admin connections": (0, "medium"),
    "scan for startup procs": (0, "medium"),
    "external scripts enabled": (0, "medium"),
    # LOW RISK - monitoring/info
    "show advanced options": (0, "low"),
    "default trace enabled": (1, "low"),
}

# System databases to skip for per-db queries
SYSTEM_DBS = ("master", "tempdb", "model", "msdb")


class AuditDataCollector:
    """
    Collects audit data from SQL Server and writes to Excel.

    This class encapsulates all the data collection logic needed
    for a comprehensive security audit. Optionally stores findings
    to SQLite for diff-based finalize workflow.
    """

    def __init__(
        self,
        connector: SqlConnector,
        query_provider: QueryProvider,
        writer: EnhancedReportWriter,
        db_conn=None,
        audit_run_id: int | None = None,
        instance_id: int | None = None,
        expected_builds: dict[str, str] | None = None,  # NEW: {sql_year: expected_version}
    ) -> None:
        """
        Initialize collector.

        Args:
            connector: SQL Server connection
            query_provider: Version-appropriate query provider
            writer: Excel report writer to populate
            db_conn: SQLite connection for findings storage (optional)
            audit_run_id: Current audit run ID (required if db_conn set)
            instance_id: Instance ID for this target (required if db_conn set)
            expected_builds: Dict mapping SQL year to expected version string
        """
        self.conn = connector
        self.prov = query_provider
        self.writer = writer
        # SQLite storage (optional)
        self._db_conn = db_conn
        self._audit_run_id = audit_run_id
        self._instance_id = instance_id
        # Track server/instance for entity keys
        self._server_name = ""
        self._instance_name = ""
        # Version compliance checking
        self._expected_builds = expected_builds or {}

    def _save_finding(
        self,
        finding_type: str,
        entity_name: str,
        status: str,
        risk_level: str | None = None,
        description: str | None = None,
        recommendation: str | None = None,
        details: str | None = None,
    ) -> None:
        """
        Save a finding to SQLite if db_conn is set.

        Args:
            finding_type: Type of finding (login, config, etc.)
            entity_name: Specific entity name
            status: PASS, FAIL, or WARN
            risk_level: critical, high, medium, low
            description: What was found
            recommendation: What to do about it
            details: JSON string with extra details
        """
        if self._db_conn is None or self._audit_run_id is None:
            return

        from autodbaudit.infrastructure.sqlite.schema import (
            save_finding,
            build_entity_key,
        )

        entity_key = build_entity_key(
            self._server_name, self._instance_name or "(Default)", entity_name
        )

        save_finding(
            connection=self._db_conn,
            audit_run_id=self._audit_run_id,
            instance_id=self._instance_id,
            entity_key=entity_key,
            finding_type=finding_type,
            entity_name=entity_name,
            status=status,
            risk_level=risk_level,
            finding_description=description,
            recommendation=recommendation,
            details=details,
        )
    
    def _check_version_compliance(
        self, version: str, version_major: int
    ) -> tuple[str, str]:
        """
        Check if SQL Server version matches expected build.
        
        Args:
            version: Current full version string (e.g. "16.0.4100.1")
            version_major: Major version number
            
        Returns:
            Tuple of (status, note) - status is PASS/WARN, note is description
        """
        from autodbaudit.infrastructure.excel.base import get_sql_year
        
        sql_year = get_sql_year(version_major)
        
        # If no expected builds configured, assume current
        if not self._expected_builds:
            return "PASS", ""
        
        # Check if this major version has an expected build
        expected = self._expected_builds.get(sql_year)
        if not expected:
            # No expectation for this version = assume current
            return "PASS", ""
        
        # Compare versions
        if version == expected:
            return "PASS", f"At expected build {expected}"
        
        # Version mismatch - show update available
        return "WARN", f"Current: {version}, Expected: {expected}"

    def collect_all(
        self,
        server_name: str,
        instance_name: str,
        config_name: str = "",
        ip_address: str = "",
    ) -> dict:
        """
        Collect all audit data for an instance.

        Args:
            server_name: Server hostname
            instance_name: Instance name (empty for default)
            config_name: Display name from config
            ip_address: IP address from config

        Returns:
            Dict with counts per category
        """
        # Store for entity key generation
        self._server_name = server_name
        self._instance_name = instance_name

        counts = {}
        sn = server_name
        inst = instance_name

        # 1. Instance Properties
        counts["instances"] = self._collect_instance(sn, inst, config_name, ip_address)

        # 2. SA Account (from logins)
        logins = self._get_logins()
        counts["sa"] = self._collect_sa_account(sn, inst, logins)

        # 3. Server Logins
        counts["logins"] = self._collect_logins(sn, inst, logins)

        # 4. Server Roles
        counts["roles"] = self._collect_roles(sn, inst)

        # 5. Configuration (sp_configure)
        counts["config"] = self._collect_config(sn, inst)

        # 6. Services
        counts["services"] = self._collect_services(sn, inst)

        # 7. Databases
        all_dbs, user_dbs = self._collect_databases(sn, inst)
        counts["databases"] = len(all_dbs)

        # 8. Database Users
        counts["db_users"] = self._collect_db_users(sn, inst, user_dbs)

        # 9. Database Roles
        counts["db_roles"] = self._collect_db_roles(sn, inst, user_dbs)

        # 10. Linked Servers
        counts["linked"] = self._collect_linked_servers(sn, inst)

        # 11. Triggers
        counts["triggers"] = self._collect_triggers(sn, inst, user_dbs)

        # 12. Backups
        counts["backups"] = self._collect_backups(sn, inst)

        # 13. Audit Settings
        counts["audit"] = self._collect_audit_settings(sn, inst)

        # 14. Encryption (SMK, DMK, TDE)
        counts["encryption"] = self._collect_encryption(sn, inst)

        # 15. Permission Grants (New)
        counts["permissions"] = self._collect_permissions(sn, inst, user_dbs)

        return counts

    def _get_logins(self) -> list[dict]:
        """Get server logins (reused for SA detection)."""
        return self.conn.execute_query(self.prov.get_server_logins())

    def _collect_instance(
        self, sn: str, inst: str, config_name: str, config_ip: str
    ) -> int:
        """Collect instance properties."""
        try:
            props = self.conn.execute_query(self.prov.get_instance_properties())
            if not props:
                return 0
            p = props[0]

            # Build OS info
            os_distro = p.get("OSDistribution", "")
            os_release = p.get("OSRelease", "")
            os_platform = p.get("OSPlatform", "")
            if os_distro:
                os_info = f"{os_distro} ({os_release})" if os_release else os_distro
            elif os_platform:
                os_info = os_platform
            else:
                os_info = (
                    "Windows"
                    if "Windows" in str(p.get("FullVersionString", ""))
                    else ""
                )

            # IP handling
            dmv_ip = p.get("IPAddress", "")
            tcp_port = p.get("TCPPort")
            if config_ip and dmv_ip and config_ip != dmv_ip:
                ip_address = f"{config_ip} ({dmv_ip})"
            else:
                ip_address = config_ip or dmv_ip
            
            # Version compliance check
            version = p.get("Version", "")
            version_major = p.get("VersionMajor", 0)
            version_status, version_note = self._check_version_compliance(
                version, version_major
            )

            self.writer.add_instance(
                config_name=config_name or sn,
                server_name=sn,
                instance_name=inst,
                machine_name=p.get("MachineName") or p.get("PhysicalMachine", ""),
                ip_address=ip_address,
                tcp_port=tcp_port,
                version=version,
                version_major=version_major,
                edition=p.get("Edition", ""),
                product_level=p.get("ProductLevel", ""),
                is_clustered=bool(p.get("IsClustered")),
                is_hadr=bool(p.get("IsHadrEnabled")),
                os_info=os_info,
                cpu_count=p.get("CPUCount"),
                memory_gb=p.get("MemoryGB"),
                cu_level=p.get("CULevel", ""),
                build_number=p.get("BuildNumber"),
                version_status=version_status,
                version_status_note=version_note,
            )
            
            # Save version finding if not compliant
            if version_status == "WARN":
                from autodbaudit.infrastructure.excel.base import get_sql_year
                sql_year = get_sql_year(version_major)
                expected = self._expected_builds.get(sql_year, "unknown")
                
                self._save_finding(
                    finding_type="version",
                    entity_name=f"sql_version_{sql_year}",
                    status="WARN",
                    risk_level="medium",
                    description=f"SQL {sql_year} at {version}, expected {expected}",
                    recommendation=f"Update to SQL Server {sql_year} build {expected}",
                )
            
            return 1
        except Exception as e:
            logger.warning("Instance properties failed: %s", e)
            return 0

    def _collect_sa_account(self, sn: str, inst: str, logins: list[dict]) -> int:
        """Collect SA account status."""
        for lg in logins:
            if bool(lg.get("IsSA")):
                login_name = lg.get("LoginName", "")
                is_disabled = bool(lg.get("IsDisabled"))
                is_renamed = login_name.lower() != "sa"

                self.writer.add_sa_account(
                    server_name=sn,
                    instance_name=inst,
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

                self._save_finding(
                    finding_type="sa_account",
                    entity_name="sa",
                    status=status,
                    risk_level="critical" if not is_disabled else None,
                    description=desc,
                    recommendation="Disable SA account" if not is_disabled else None,
                )
                return 1
        return 0

    def _collect_logins(self, sn: str, inst: str, logins: list[dict]) -> int:
        """Collect server logins."""
        for lg in logins:
            login_name = lg.get("LoginName", "")
            login_type = lg.get("LoginType", "")
            is_disabled = bool(lg.get("IsDisabled"))
            pwd_policy = lg.get("PasswordPolicyEnforced")

            self.writer.add_login(
                server_name=sn,
                instance_name=inst,
                login_name=login_name,
                login_type=login_type,
                is_disabled=is_disabled,
                pwd_policy=pwd_policy,
                default_db=lg.get("DefaultDatabase", ""),
            )

            # Persist to SQLite (optional - don't break collection if this fails)
            if self._db_conn and self._instance_id:
                try:
                    from autodbaudit.infrastructure.sqlite.schema import save_login

                    save_login(
                        connection=self._db_conn,
                        instance_id=self._instance_id,
                        audit_run_id=self._audit_run_id,
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
                    pass  # SQLite storage is optional

            # SQL logins (not Windows auth) are findings
            if login_type == "SQL_LOGIN" and not is_disabled:
                self._save_finding(
                    finding_type="login",
                    entity_name=login_name,
                    status="WARN",
                    risk_level="medium",
                    description=f"SQL login '{login_name}' (not Windows auth)",
                    recommendation="Consider Windows authentication where possible",
                )
            # Disabled logins with policy issues
            elif not pwd_policy and login_type == "SQL_LOGIN":
                self._save_finding(
                    finding_type="login",
                    entity_name=login_name,
                    status="FAIL",
                    risk_level="high",
                    description=f"SQL login '{login_name}' without password policy",
                    recommendation="Enable password policy enforcement",
                )
        return len(logins)

    def _collect_roles(self, sn: str, inst: str) -> int:
        """Collect server role memberships."""
        try:
            roles = self.conn.execute_query(self.prov.get_server_role_members())
            for r in roles:
                self.writer.add_role_member(
                    server_name=sn,
                    instance_name=inst,
                    role_name=r.get("RoleName", ""),
                    member_name=r.get("MemberName", ""),
                    member_type=r.get("MemberType", ""),
                    is_disabled=bool(r.get("MemberDisabled")),
                )
            return len(roles)
        except Exception as e:
            logger.warning("Roles failed: %s", e)
            return 0

    def _collect_config(self, sn: str, inst: str) -> int:
        """Collect sp_configure security settings."""
        try:
            configs = self.conn.execute_query(self.prov.get_sp_configure())
            count = 0
            for cfg in configs:
                setting_name = cfg.get("SettingName", "")
                setting_key = setting_name.lower()

                # Match against security settings
                for key, (required, default_risk) in SECURITY_SETTINGS.items():
                    if key.lower() == setting_key:
                        current = cfg.get("RunningValue", 0) or 0
                        configured = cfg.get("ConfiguredValue", 0) or 0
                        is_dynamic = bool(cfg.get("IsDynamic", 0))

                        is_compliant = int(current) == required
                        is_config_compliant = int(configured) == required

                        status = "PASS"
                        risk = None
                        desc = f"{setting_name}={current} (required: {required})"
                        rec = None

                        if not is_compliant:
                            if is_config_compliant:
                                # Config changed but value not active
                                status = "WARN"
                                risk = "medium"
                                if not is_dynamic:
                                    desc += " [Pending SQL Restart]"
                                    rec = "Restart SQL Server service to apply changes"
                                else:
                                    desc += " [Pending RECONFIGURE]"
                                    rec = "Run RECONFIGURE statement to apply changes"
                            else:
                                # Neither compliant nor configured
                                status = "FAIL"
                                risk = default_risk
                                rec = f"Set {setting_name} to {required}"

                        self.writer.add_config_setting(
                            server_name=sn,
                            instance_name=inst,
                            setting_name=setting_name,
                            current_value=int(current),
                            required_value=required,
                            risk_level=(
                                risk if status != "PASS" else "low"
                            ),  # Low risk for pass
                        )

                        # Persist to SQLite (optional - don't break collection if this fails)
                        if self._db_conn and self._instance_id:
                            try:
                                from autodbaudit.infrastructure.sqlite.schema import (
                                    save_config_setting,
                                )

                                save_config_setting(
                                    connection=self._db_conn,
                                    instance_id=self._instance_id,
                                    audit_run_id=self._audit_run_id,
                                    setting_name=setting_name,
                                    configured_value=int(configured),
                                    running_value=int(current),
                                    required_value=required,
                                    status=status,
                                    risk_level=risk,
                                )
                            except Exception:
                                pass  # SQLite storage is optional

                        # Save finding to SQLite
                        self._save_finding(
                            finding_type="config",
                            entity_name=setting_name,
                            status=status,
                            risk_level=risk,
                            description=desc,
                            recommendation=rec,
                        )
                        count += 1
                        break
            return count
        except Exception as e:
            logger.warning("Config failed: %s", e)
            return 0

    def _collect_services(self, sn: str, inst: str) -> int:
        """Collect SQL Server services."""
        try:
            services = self.conn.execute_query(self.prov.get_sql_services())
            for svc in services:
                svc_instance = svc.get("InstanceName") or inst or "(Default)"
                svc_type = svc.get("ServiceType", "Other")
                if svc_type in ("SQL Browser", "VSS Writer", "Integration Services"):
                    svc_instance = "(Shared)"

                self.writer.add_service(
                    server_name=sn,
                    instance_name=svc_instance,
                    service_name=svc.get("ServiceName") or svc.get("DisplayName", ""),
                    service_type=svc_type,
                    status=svc.get("Status", "Unknown"),
                    startup_type=svc.get("StartupType", ""),
                    service_account=svc.get("ServiceAccount", ""),
                )
            return len(services)
        except Exception as e:
            logger.warning("Services failed: %s", e)
            return 0

    def _collect_databases(self, sn: str, inst: str) -> tuple[list[dict], list[dict]]:
        """Collect databases, returns (all_dbs, user_dbs)."""
        try:
            dbs = self.conn.execute_query(self.prov.get_databases())
            user_dbs = [db for db in dbs if db.get("DatabaseName") not in SYSTEM_DBS]

            for db in dbs:
                db_name = db.get("DatabaseName", "")
                is_trustworthy = bool(db.get("IsTrustworthy"))

                self.writer.add_database(
                    server_name=sn,
                    instance_name=inst,
                    database_name=db_name,
                    owner=db.get("Owner", ""),
                    recovery_model=db.get("RecoveryModel", ""),
                    state=db.get("State", ""),
                    data_size_mb=db.get("DataSizeMB") or db.get("SizeMB"),
                    log_size_mb=db.get("LogSizeMB"),
                    is_trustworthy=is_trustworthy,
                )

                # Persist to SQLite (optional - don't break collection if this fails)
                if self._db_conn and self._instance_id:
                    try:
                        from autodbaudit.infrastructure.sqlite.schema import (
                            save_database,
                        )

                        save_database(
                            connection=self._db_conn,
                            instance_id=self._instance_id,
                            audit_run_id=self._audit_run_id,
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
                        pass  # SQLite storage is optional

                # Trustworthy flag is a finding
                if is_trustworthy and db_name not in SYSTEM_DBS:
                    self._save_finding(
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

    def _collect_db_users(self, sn: str, inst: str, user_dbs: list[dict]) -> int:
        """Collect database users from all user databases."""
        count = 0
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
                        server_name=sn,
                        instance_name=inst,
                        database_name=db_name,
                        user_name=user_name,
                        user_type=user_type,
                        mapped_login=mapped_login,
                        is_orphaned=is_orphaned,
                        has_connect=(
                            guest_enabled if user_name.lower() == "guest" else True
                        ),
                    )

                    # Persist to SQLite (optional - don't break collection if this fails)
                    if self._db_conn and self._instance_id:
                        try:
                            from autodbaudit.infrastructure.sqlite.schema import (
                                save_db_user,
                            )

                            save_db_user(
                                connection=self._db_conn,
                                instance_id=self._instance_id,
                                audit_run_id=self._audit_run_id,
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
                            pass  # SQLite storage is optional

                    count += 1

                    # Orphaned user finding
                    if is_orphaned:
                        self.writer.add_orphaned_user(
                            server_name=sn,
                            instance_name=inst,
                            database_name=db_name,
                            user_name=user_name,
                            user_type=user_type,
                        )
                        self._save_finding(
                            finding_type="db_user",
                            entity_name=f"{db_name}|{user_name}",
                            status="WARN",
                            risk_level="medium",
                            description=f"Orphaned user '{user_name}' in database '{db_name}'",
                            recommendation="Remove or remap orphaned user",
                        )

                    # Guest enabled finding
                    if user_name.lower() == "guest" and guest_enabled:
                        self._save_finding(
                            finding_type="db_user",
                            entity_name=f"{db_name}|guest",
                            status="FAIL",
                            risk_level="high",
                            description=f"Guest user enabled in database '{db_name}'",
                            recommendation="Disable guest user access",
                        )
            except Exception:
                pass
        return count

    def _collect_db_roles(self, sn: str, inst: str, user_dbs: list[dict]) -> int:
        """Collect database role memberships."""
        count = 0
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            if db.get("State", "ONLINE") != "ONLINE":
                continue
            try:
                roles = self.conn.execute_query(
                    self.prov.get_database_role_members(db_name)
                )

                # Aggregate for Matrix View (User -> [Roles])
                # Key: (MemberName, MemberType) -> List[RoleName]
                user_matrix: dict[tuple[str, str], list[str]] = {}

                for r in roles:
                    role_name = r.get("RoleName", "")
                    member_name = r.get("MemberName", "")
                    member_type = r.get("MemberType", "")

                    # Add to standard sheet
                    self.writer.add_db_role_member(
                        server_name=sn,
                        instance_name=inst,
                        database_name=db_name,
                        role_name=role_name,
                        member_name=member_name,
                        member_type=member_type,
                    )

                    # Add to aggregation
                    key = (member_name, member_type)
                    if key not in user_matrix:
                        user_matrix[key] = []
                    user_matrix[key].append(role_name)

                    # Persist to SQLite
                    if self._db_conn and self._instance_id:
                        try:
                            from autodbaudit.infrastructure.sqlite.schema import (
                                save_database_role_member,
                            )

                            save_database_role_member(
                                connection=self._db_conn,
                                audit_run_id=self._audit_run_id,
                                instance_id=self._instance_id,
                                database_name=db_name,
                                role_name=role_name,
                                member_name=member_name,
                                member_type=member_type,
                            )
                        except Exception:
                            pass

                    count += 1

                # Write Matrix Rows
                for (m_name, m_type), m_roles in user_matrix.items():
                    self.writer.add_role_matrix_row(
                        server_name=sn,
                        instance_name=inst,
                        database_name=db_name,
                        principal_name=m_name,
                        principal_type=m_type,
                        roles=m_roles,
                    )

            except Exception:
                pass
        return count

    def _collect_linked_servers(self, sn: str, inst: str) -> int:
        """Collect linked server configuration."""
        try:
            linked = self.conn.execute_query(self.prov.get_linked_servers())
            login_mappings = self.conn.execute_query(
                self.prov.get_linked_server_logins()
            )

            # Build mapping dict
            mapping_info: dict[str, tuple[str, str, bool, str]] = {}
            for m in login_mappings:
                ls_name = m.get("LinkedServerName", "")
                remote = m.get("RemoteLogin") or ""
                local = m.get("LocalLogin", "")
                impersonate = bool(m.get("Impersonate"))
                risk = m.get("RiskLevel", "NORMAL")
                if ls_name not in mapping_info or risk == "HIGH_PRIVILEGE":
                    mapping_info[ls_name] = (local, remote, impersonate, risk)

            for ls in linked:
                ls_name = ls.get("LinkedServerName", "")
                local, remote, impersonate, risk = mapping_info.get(
                    ls_name, ("", "", False, "")
                )
                rpc_out = bool(ls.get("RpcOutEnabled"))

                self.writer.add_linked_server(
                    server_name=sn,
                    instance_name=inst,
                    linked_server_name=ls_name,
                    product=ls.get("Product") or "",
                    provider=ls.get("Provider") or "",
                    data_source=ls.get("DataSource") or "",
                    rpc_out=rpc_out,
                    local_login=local,
                    remote_login=remote,
                    impersonate=impersonate,
                    risk_level=risk,
                )

                # Persist to SQLite (optional - don't break collection if this fails)
                if self._db_conn and self._instance_id:
                    try:
                        from autodbaudit.infrastructure.sqlite.schema import (
                            save_linked_server,
                        )

                        save_linked_server(
                            connection=self._db_conn,
                            instance_id=self._instance_id,
                            audit_run_id=self._audit_run_id,
                            linked_server_name=ls_name,
                            product=ls.get("Product") or "",
                            provider=ls.get("Provider") or "",
                            data_source=ls.get("DataSource") or "",
                            is_rpc_out_enabled=rpc_out,
                            local_login=local,
                            remote_login=remote,
                            is_impersonate=impersonate,
                        )
                    except Exception:
                        pass  # SQLite storage is optional

                # High privilege linked server finding
                if risk == "HIGH_PRIVILEGE":
                    self._save_finding(
                        finding_type="linked_server",
                        entity_name=ls_name,
                        status="FAIL",
                        risk_level="high",
                        description=f"Linked server '{ls_name}' with high privilege mapping",
                        recommendation="Review linked server credentials and access",
                    )
                elif rpc_out:
                    self._save_finding(
                        finding_type="linked_server",
                        entity_name=ls_name,
                        status="WARN",
                        risk_level="medium",
                        description=f"Linked server '{ls_name}' has RPC out enabled",
                        recommendation="Disable RPC out if not required",
                    )
            return len(linked)
        except Exception as e:
            logger.warning("Linked servers failed: %s", e)
            return 0

    def _collect_triggers(self, sn: str, inst: str, user_dbs: list[dict]) -> int:
        """Collect server and database triggers."""
        count = 0

        # Server-level triggers
        try:
            triggers = self.conn.execute_query(self.prov.get_server_triggers())
            for t in triggers:
                self.writer.add_trigger(
                    server_name=sn,
                    instance_name=inst,
                    level="SERVER",
                    database_name=None,
                    trigger_name=t.get("TriggerName", ""),
                    event_type=t.get("EventType", ""),
                    is_enabled=not bool(t.get("IsDisabled")),
                )
                count += 1
        except Exception:
            pass

        # Database-level triggers
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
                        server_name=sn,
                        instance_name=inst,
                        level="DATABASE",
                        database_name=db_name,
                        trigger_name=t.get("TriggerName", ""),
                        event_type=t.get("EventType", ""),
                        is_enabled=not bool(t.get("IsDisabled")),
                    )
                    count += 1
            except Exception:
                pass
        return count

    def _collect_backups(self, sn: str, inst: str) -> int:
        """Collect backup history."""
        try:
            backups = self.conn.execute_query(self.prov.get_backup_history())
            for b in backups:
                db_name = b.get("DatabaseName", "")
                days_since = b.get("DaysSinceBackup")

                self.writer.add_backup_info(
                    server_name=sn,
                    instance_name=inst,
                    database_name=db_name,
                    recovery_model=b.get("RecoveryModel", ""),
                    last_backup_date=b.get("BackupDate"),
                    days_since=days_since,
                    backup_path=b.get("BackupPath", ""),
                    backup_size_mb=b.get("BackupSizeMB"),
                )

                # Persist to SQLite (optional - don't break collection if this fails)
                if self._db_conn and self._instance_id:
                    try:
                        from autodbaudit.infrastructure.sqlite.schema import (
                            save_backup_record,
                        )

                        save_backup_record(
                            connection=self._db_conn,
                            instance_id=self._instance_id,
                            audit_run_id=self._audit_run_id,
                            database_name=db_name,
                            backup_type=b.get("BackupType", "FULL"),
                            backup_start=(
                                str(b.get("BackupDate"))
                                if b.get("BackupDate")
                                else None
                            ),
                            size_bytes=int((b.get("BackupSizeMB") or 0) * 1024 * 1024),
                            physical_device_name=b.get("BackupPath", ""),
                        )
                    except Exception:
                        pass  # SQLite storage is optional

                # Backup findings
                if days_since is None:
                    self._save_finding(
                        finding_type="backup",
                        entity_name=db_name,
                        status="FAIL",
                        risk_level="critical",
                        description=f"Database '{db_name}' has no backup",
                        recommendation="Create backup immediately",
                    )
                elif days_since > 7:
                    self._save_finding(
                        finding_type="backup",
                        entity_name=db_name,
                        status="WARN",
                        risk_level="high" if days_since > 30 else "medium",
                        description=f"Database '{db_name}' backup is {days_since} days old",
                        recommendation="Review backup schedule",
                    )
            return len(backups)
        except Exception as e:
            logger.warning("Backups failed: %s", e)
            return 0

    def _collect_audit_settings(self, sn: str, inst: str) -> int:
        """Collect audit settings."""
        try:
            audit = self.conn.execute_query(self.prov.get_audit_settings())
            for a in audit:
                self.writer.add_audit_setting(
                    server_name=sn,
                    instance_name=inst,
                    setting_name=a.get("SettingName", "Login Auditing"),
                    current_value=a.get("CurrentValue", ""),
                    recommended_value="All",
                )
            return len(audit)
        except Exception as e:
            logger.warning("Audit settings failed: %s", e)
            return 0

    def _collect_encryption(self, sn: str, inst: str) -> int:
        """Collect encryption status (SMK, DMK, TDE)."""
        count = 0

        # 1. Service Master Key (instance-level)
        try:
            smk = self.conn.execute_query(self.prov.get_service_master_key())
            if smk:
                s = smk[0]
                self.writer.add_encryption_row(
                    server_name=sn,
                    instance_name=inst,
                    database_name="(Instance)",
                    key_type="SMK",
                    key_name=s.get("KeyName", "##MS_ServiceMasterKey##"),
                    algorithm=s.get("Algorithm", ""),
                    created_date=s.get("CreatedDate"),
                    backup_status="N/A",  # Can't easily track SMK backup
                    status="PASS",  # SMK always exists
                )
                count += 1
            else:
                # Edge case: no SMK found (unlikely)
                self.writer.add_encryption_row(
                    server_name=sn,
                    instance_name=inst,
                    database_name="(Instance)",
                    key_type="SMK",
                    key_name="(Not Found)",
                    algorithm="",
                    created_date=None,
                    backup_status="N/A",
                    status="WARN",
                )
                count += 1
        except Exception as e:
            logger.warning("SMK query failed: %s", e)

        # 2. Database Master Keys
        try:
            dmks = self.conn.execute_query(self.prov.get_database_master_keys())
            for d in dmks:
                self.writer.add_encryption_row(
                    server_name=sn,
                    instance_name=inst,
                    database_name=d.get("DatabaseName", ""),
                    key_type="DMK",
                    key_name=d.get("KeyName", "##MS_DatabaseMasterKey##"),
                    algorithm=d.get("Algorithm", ""),
                    created_date=d.get("CreatedDate"),
                    backup_status="⚠️ Not Backed Up",  # Default assumption
                    status="WARN",
                )
                count += 1
        except Exception as e:
            logger.warning("DMK query failed: %s", e)

        # 3. TDE Status
        try:
            tde = self.conn.execute_query(self.prov.get_tde_status())
            for t in tde:
                enc_state = t.get("EncryptionState") or 0
                enc_desc = t.get("EncryptionStateDesc", "")
                is_encrypted = enc_state == 3 or bool(t.get("IsEncrypted"))

                if is_encrypted:
                    cert_name = t.get("CertificateName", "")
                    self.writer.add_encryption_row(
                        server_name=sn,
                        instance_name=inst,
                        database_name=t.get("DatabaseName", ""),
                        key_type="TDE",
                        key_name=cert_name or "DEK",
                        algorithm=t.get("Algorithm", ""),
                        created_date=t.get("CreatedDate"),
                        backup_status="✓ Backed Up" if cert_name else "⚠️ Not Backed Up",
                        status="PASS" if cert_name else "WARN",
                    )
                    count += 1
        except Exception as e:
            logger.warning("TDE query failed: %s", e)

        # If no encryption found at all, add informational row
        if count == 0:
            self.writer.add_encryption_row(
                server_name=sn,
                instance_name=inst,
                database_name="(Instance)",
                key_type="N/A",
                key_name="No encryption configured",
                algorithm="",
                created_date=None,
                backup_status="N/A",
                status="N/A",
            )
            count = 1

        return count

    def _collect_permissions(self, sn: str, inst: str, user_dbs: list[dict]) -> int:
        """Collect server and database permission grants."""
        count = 0
        from autodbaudit.infrastructure.sqlite.schema import save_permission

        # 1. Server Permissions
        try:
            srv_perms = self.conn.execute_query(self.prov.get_server_permissions())
            for p in srv_perms:
                self.writer.add_permission(
                    server_name=sn,
                    instance_name=inst,
                    scope="SERVER",
                    database_name="",
                    grantee_name=p.get("GranteeName", ""),
                    permission_name=p.get("PermissionName", ""),
                    state=p.get("PermissionState", ""),
                    entity_name=p.get("EntityName", ""),
                    class_desc=p.get("PermissionClass", ""),
                )

                # Persist
                if self._db_conn and self._instance_id:
                    try:
                        save_permission(
                            connection=self._db_conn,
                            audit_run_id=self._audit_run_id,
                            instance_id=self._instance_id,
                            scope="SERVER",
                            database_name="",
                            entity_name=p.get("EntityName", ""),
                            grantee_name=p.get("GranteeName", ""),
                            permission_name=p.get("PermissionName", ""),
                            state=p.get("PermissionState", ""),
                            class_desc=p.get("PermissionClass", ""),
                        )
                    except Exception:
                        pass
                count += 1
        except Exception as e:
            logger.warning("Server permissions failed: %s", e)

        # 2. Database Permissions
        for db in user_dbs:
            db_name = db.get("DatabaseName", "")
            if db.get("State", "ONLINE") != "ONLINE":
                continue
            try:
                db_perms = self.conn.execute_query(
                    self.prov.get_database_permissions(db_name)
                )
                for p in db_perms:
                    self.writer.add_permission(
                        server_name=sn,
                        instance_name=inst,
                        scope="DATABASE",
                        database_name=db_name,
                        grantee_name=p.get("GranteeName", ""),
                        permission_name=p.get("PermissionName", ""),
                        state=p.get("PermissionState", ""),
                        entity_name=p.get("EntityName", ""),
                        class_desc=p.get("PermissionClass", ""),
                    )

                    # Persist
                    if self._db_conn and self._instance_id:
                        try:
                            save_permission(
                                connection=self._db_conn,
                                audit_run_id=self._audit_run_id,
                                instance_id=self._instance_id,
                                scope="DATABASE",
                                database_name=db_name,
                                entity_name=p.get("EntityName", ""),
                                grantee_name=p.get("GranteeName", ""),
                                permission_name=p.get("PermissionName", ""),
                                state=p.get("PermissionState", ""),
                                class_desc=p.get("PermissionClass", ""),
                            )
                        except Exception:
                            pass
                    count += 1
            except Exception:
                pass

        return count
