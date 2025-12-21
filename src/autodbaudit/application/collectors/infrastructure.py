"""
Collector for Infrastructure (Services, Protocols, Backups, Linked Servers).
"""

from __future__ import annotations

import logging
from autodbaudit.application.collectors.base import BaseCollector

logger = logging.getLogger(__name__)


class InfrastructureCollector(BaseCollector):
    """
    Collects infrastructure and operational configuration.
    """

    def collect(self) -> dict[str, int]:
        """
        Collect infrastructure data.
        Returns dict with counts.
        """
        return {
            "services": self._collect_services(),
            "protocols": self._collect_client_protocols(),
            "linked": self._collect_linked_servers(),
            "backups": self._collect_backups(),
        }

    def _collect_services(self) -> int:
        """Collect SQL Server services."""
        try:
            services = self.conn.execute_query(self.prov.get_sql_services())
            for svc in services:
                svc_instance = (
                    svc.get("InstanceName") or self.ctx.instance_name or "(Default)"
                )
                svc_type = svc.get("ServiceType", "Other")
                if svc_type in ("SQL Browser", "VSS Writer", "Integration Services"):
                    svc_instance = "(Shared)"

                self.writer.add_service(
                    server_name=self.ctx.server_name,
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

    def _collect_client_protocols(self) -> int:
        """Collect client network protocol configuration."""
        try:
            protocols = self.conn.execute_query(self.prov.get_client_protocols())
            for proto in protocols:
                self.writer.add_client_protocol(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    protocol_name=proto.get("ProtocolName", ""),
                    is_enabled=bool(proto.get("IsEnabled", 0)),
                    port=proto.get("DefaultPort"),
                    notes=proto.get("Notes", ""),
                )
            return len(protocols)
        except Exception as e:
            logger.warning("Client protocols failed: %s", e)
            return 0

    def _collect_linked_servers(self) -> int:
        """Collect linked servers with login mappings."""
        try:
            # Get linked server base info
            linked = self.conn.execute_query(self.prov.get_linked_servers())
            
            # Get linked server login mappings (contains risk_level!)
            logins = self.conn.execute_query(self.prov.get_linked_server_logins())
            
            # Build lookup: linked_server_name -> list of login mappings
            login_map: dict[str, list[dict]] = {}
            for lg in logins:
                ls_name = lg.get("LinkedServerName", "")
                if ls_name:
                    if ls_name not in login_map:
                        login_map[ls_name] = []
                    login_map[ls_name].append(lg)
            
            count = 0
            for ls in linked:
                # FIXED: Query returns LinkedServerName, not ServerName
                ls_name = ls.get("LinkedServerName", "")
                # FIXED: Query returns Provider and Product, not ProviderName/ProductName
                provider = ls.get("Provider", "")
                product = ls.get("Product", "")
                data_source = ls.get("DataSource", "")
                is_rpc_out_enabled = bool(ls.get("RpcOutEnabled"))
                
                # Get login mappings for this linked server
                mappings = login_map.get(ls_name, [])
                
                if mappings:
                    # One row per login mapping (can be multiple per linked server)
                    for mapping in mappings:
                        local_login = mapping.get("LocalLogin", "")
                        remote_login = mapping.get("RemoteLogin", "")
                        impersonate = bool(mapping.get("Impersonate"))
                        risk_level = mapping.get("RiskLevel", "")
                        
                        self.writer.add_linked_server(
                            server_name=self.ctx.server_name,
                            instance_name=self.ctx.instance_name,
                            linked_server_name=ls_name,
                            product=product,
                            provider=provider,
                            data_source=data_source,
                            rpc_out=is_rpc_out_enabled,
                            local_login=local_login,
                            remote_login=remote_login,
                            impersonate=impersonate,
                            risk_level=risk_level,
                        )
                        count += 1
                        
                        # Security check: High privilege = discrepant
                        if risk_level == "HIGH_PRIVILEGE":
                            self.save_finding(
                                finding_type="linked_server",
                                entity_name=f"{ls_name}|{local_login}|{remote_login}",
                                status="FAIL",
                                risk_level="high",
                                description=f"Linked server '{ls_name}' uses high-privilege remote login '{remote_login}'",
                                recommendation="Use least-privilege credentials for linked server connections",
                            )
                else:
                    # No login mappings - still add the linked server
                    self.writer.add_linked_server(
                        server_name=self.ctx.server_name,
                        instance_name=self.ctx.instance_name,
                        linked_server_name=ls_name,
                        product=product,
                        provider=provider,
                        data_source=data_source,
                        rpc_out=is_rpc_out_enabled,
                    )
                    count += 1
                    
                    # Warn if RPC Out is enabled (less critical than high-priv creds)
                    if is_rpc_out_enabled:
                        self.save_finding(
                            finding_type="linked_server",
                            entity_name=ls_name,
                            status="WARN",
                            risk_level="medium",
                            description=f"Linked server '{ls_name}' has RPC Out enabled",
                            recommendation="Disable RPC Out unless required",
                        )
            
            return count
        except Exception as e:
            logger.warning("Linked servers failed: %s", e)
            return 0

    def _collect_backups(self) -> int:
        """Collect backup history."""
        try:
            backups = self.conn.execute_query(self.prov.get_backup_history())
            for bak in backups:
                db_name = bak.get("DatabaseName", "")
                recovery_model = bak.get("RecoveryModel", "")
                last_full = bak.get("LastFullBackup")
                # last_diff and last_log retrieved but currently unused in report
                # last_diff = bak.get("LastDiffBackup")
                last_log = bak.get("LastLogBackup")

                self.writer.add_backup_info(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    database_name=db_name,
                    recovery_model=recovery_model,
                    last_backup_date=last_full,
                    days_since=bak.get("DaysSinceBackup"),
                    backup_path=bak.get("BackupPath", ""),
                    backup_size_mb=bak.get("BackupSizeMB"),
                )

                if not last_full:
                    self.save_finding(
                        finding_type="backup",
                        entity_name=f"{db_name}|full",
                        status="FAIL",
                        risk_level="high",
                        description=f"Database '{db_name}' has no recent FULL backup",
                        recommendation="Ensure regular backup schedule is running",
                    )
                elif recovery_model == "FULL" and not last_log:
                    self.save_finding(
                        finding_type="backup",
                        entity_name=f"{db_name}|log",
                        status="WARN",
                        risk_level="medium",
                        description=f"Database '{db_name}' is in FULL recovery but has no LOG backups",
                        recommendation="Schedule transaction log backups or switch to SIMPLE recovery",
                    )
            return len(backups)
        except Exception as e:
            logger.warning("Backups failed: %s", e)
            return 0
