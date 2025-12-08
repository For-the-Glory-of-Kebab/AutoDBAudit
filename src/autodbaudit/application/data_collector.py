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
    for a comprehensive security audit.
    """
    
    def __init__(
        self,
        connector: SqlConnector,
        query_provider: QueryProvider,
        writer: EnhancedReportWriter,
    ) -> None:
        """
        Initialize collector.
        
        Args:
            connector: SQL Server connection
            query_provider: Version-appropriate query provider
            writer: Excel report writer to populate
        """
        self.conn = connector
        self.prov = query_provider
        self.writer = writer
    
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
                os_info = "Windows" if "Windows" in str(p.get("FullVersionString", "")) else ""
            
            # IP handling
            dmv_ip = p.get("IPAddress", "")
            tcp_port = p.get("TCPPort")
            if config_ip and dmv_ip and config_ip != dmv_ip:
                ip_address = f"{config_ip} ({dmv_ip})"
            else:
                ip_address = config_ip or dmv_ip
            
            self.writer.add_instance(
                config_name=config_name or sn,
                server_name=sn,
                instance_name=inst,
                machine_name=p.get("MachineName") or p.get("PhysicalMachine", ""),
                ip_address=ip_address,
                tcp_port=tcp_port,
                version=p.get("Version", ""),
                version_major=p.get("VersionMajor", 0),
                edition=p.get("Edition", ""),
                product_level=p.get("ProductLevel", ""),
                is_clustered=bool(p.get("IsClustered")),
                is_hadr=bool(p.get("IsHadrEnabled")),
                os_info=os_info,
                cpu_count=p.get("CPUCount"),
                memory_gb=p.get("MemoryGB"),
                cu_level=p.get("CULevel", ""),
                build_number=p.get("BuildNumber"),
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
                self.writer.add_sa_account(
                    server_name=sn,
                    instance_name=inst,
                    is_disabled=bool(lg.get("IsDisabled")),
                    is_renamed=login_name.lower() != "sa",
                    current_name=login_name,
                    default_db=lg.get("DefaultDatabase", "master"),
                )
                return 1
        return 0
    
    def _collect_logins(self, sn: str, inst: str, logins: list[dict]) -> int:
        """Collect server logins."""
        for lg in logins:
            self.writer.add_login(
                server_name=sn,
                instance_name=inst,
                login_name=lg.get("LoginName", ""),
                login_type=lg.get("LoginType", ""),
                is_disabled=bool(lg.get("IsDisabled")),
                pwd_policy=lg.get("PasswordPolicyEnforced"),
                default_db=lg.get("DefaultDatabase", ""),
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
                for key, (required, risk) in SECURITY_SETTINGS.items():
                    if key.lower() == setting_key:
                        current = cfg.get("RunningValue", 0) or 0
                        self.writer.add_config_setting(
                            server_name=sn,
                            instance_name=inst,
                            setting_name=setting_name,
                            current_value=int(current),
                            required_value=required,
                            risk_level=risk,
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
                self.writer.add_database(
                    server_name=sn,
                    instance_name=inst,
                    database_name=db.get("DatabaseName", ""),
                    owner=db.get("Owner", ""),
                    recovery_model=db.get("RecoveryModel", ""),
                    state=db.get("State", ""),
                    data_size_mb=db.get("DataSizeMB") or db.get("SizeMB"),
                    log_size_mb=db.get("LogSizeMB"),
                    is_trustworthy=bool(db.get("IsTrustworthy")),
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
                        mapped_login is None and
                        user_type in ("SQL_USER", "WINDOWS_USER") and
                        user_name not in ("dbo", "guest", "INFORMATION_SCHEMA", "sys")
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
                        has_connect=guest_enabled if user_name.lower() == "guest" else True,
                    )
                    count += 1
                    
                    if is_orphaned:
                        self.writer.add_orphaned_user(
                            server_name=sn,
                            instance_name=inst,
                            database_name=db_name,
                            user_name=user_name,
                            user_type=user_type,
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
                roles = self.conn.execute_query(self.prov.get_database_role_members(db_name))
                for r in roles:
                    self.writer.add_db_role_member(
                        server_name=sn,
                        instance_name=inst,
                        database_name=db_name,
                        role_name=r.get("RoleName", ""),
                        member_name=r.get("MemberName", ""),
                        member_type=r.get("MemberType", ""),
                    )
                    count += 1
            except Exception:
                pass
        return count
    
    def _collect_linked_servers(self, sn: str, inst: str) -> int:
        """Collect linked server configuration."""
        try:
            linked = self.conn.execute_query(self.prov.get_linked_servers())
            login_mappings = self.conn.execute_query(self.prov.get_linked_server_logins())
            
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
                local, remote, impersonate, risk = mapping_info.get(ls_name, ("", "", False, ""))
                
                self.writer.add_linked_server(
                    server_name=sn,
                    instance_name=inst,
                    linked_server_name=ls_name,
                    product=ls.get("Product") or "",
                    provider=ls.get("Provider") or "",
                    data_source=ls.get("DataSource") or "",
                    rpc_out=bool(ls.get("RpcOutEnabled")),
                    local_login=local,
                    remote_login=remote,
                    impersonate=impersonate,
                    risk_level=risk,
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
                    is_enabled=bool(t.get("IsEnabled")),
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
                triggers = self.conn.execute_query(self.prov.get_database_triggers(db_name))
                for t in triggers:
                    self.writer.add_trigger(
                        server_name=sn,
                        instance_name=inst,
                        level="DATABASE",
                        database_name=db_name,
                        trigger_name=t.get("TriggerName", ""),
                        event_type=t.get("EventType", ""),
                        is_enabled=bool(t.get("IsEnabled")),
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
                self.writer.add_backup_info(
                    server_name=sn,
                    instance_name=inst,
                    database_name=b.get("DatabaseName", ""),
                    recovery_model=b.get("RecoveryModel", ""),
                    last_backup_date=b.get("BackupDate"),
                    days_since=b.get("DaysSinceBackup"),
                    backup_path=b.get("BackupPath", ""),
                    backup_size_mb=b.get("BackupSizeMB"),
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
