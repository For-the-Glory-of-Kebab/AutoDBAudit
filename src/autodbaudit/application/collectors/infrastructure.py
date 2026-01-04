"""
Collector for Infrastructure (Services, Protocols, Backups, Linked Servers).
"""

from __future__ import annotations

import logging
import json
from autodbaudit.application.collectors.base import BaseCollector
from autodbaudit.infrastructure.psremoting.facade import PSRemotingFacade
from autodbaudit.utils.resources import get_base_path

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

    def _collect_services_via_tsql(self) -> int:
        """Collect services using T-SQL DMV as fallback."""
        try:
            services = self.conn.execute_query(self.prov.get_sql_services())
            if not services:
                logger.warning("No services found via T-SQL either.")
                return 0

            # Process T-SQL results
            for svc in services:
                svc_instance = (
                    svc.get("InstanceName") or self.ctx.instance_name or "(Default)"
                )
                svc_type = svc.get("ServiceType", "Other")
                if svc_type in ("SQL Browser", "VSS Writer", "Integration Services"):
                    svc_instance = "(Shared)"

                service_name = svc.get("ServiceName") or svc.get("DisplayName") or ""
                service_account = svc.get("ServiceAccount") or ""
                status = svc.get("Status") or "Unknown"
                startup_type = svc.get("StartupType") or ""

                self.writer.add_service(
                    server_name=self.ctx.server_name,
                    instance_name=svc_instance,
                    service_name=service_name,
                    service_type=svc_type,
                    status=status,
                    startup_type=startup_type,
                    service_account=service_account,
                )

                # Build entity_key: server|instance|service_name
                entity_key = (
                    f"{self.ctx.server_name}|{svc_instance}|{service_name}".lower()
                )

                # Determine if this service needs review
                finding_status, risk_level, description = self._evaluate_service_finding(
                    service_account, status, startup_type
                )

                rec_parts = []
                if "running as" in description:
                    rec_parts.append("Use managed service accounts")
                if "Auto-start service is stopped" in description:
                    rec_parts.append(
                        "Start service or change startup type to Manual/Disabled"
                    )

                self.save_finding(
                    finding_type="service",
                    entity_name=service_name,
                    status=finding_status,
                    risk_level=risk_level,
                    description=f"Service '{service_name}': {description}",
                    recommendation="; ".join(rec_parts) if rec_parts else None,
                    entity_key=entity_key,
                )

            logger.info(
                "Successfully collected %d services via T-SQL fallback.", len(services)
            )
            return len(services)

        except Exception as e:
            logger.error(
                "Services collection (T-SQL fallback) failed for %s: %s",
                self.ctx.server_name,
                e,
                exc_info=True,
            )
            return 0

    def _collect_services(self) -> int:
        """Collect service status using PowerShell (primary) with T-SQL fallback."""
        # 1. Try Primary Method: PowerShell (WMI/CIM)
        # This provides better data for OS-level services
        count = self._collect_services_via_powershell()
        if count > 0:
            logger.info("Services collected via PowerShell: %d", count)
            return count

        logger.warning("PowerShell returned no services. Attempting T-SQL fallback...")

        # 2. Fallback: T-SQL DMV
        return self._collect_services_via_tsql()

    def _load_credentials(self) -> tuple[str | None, str | None]:
        """Load credentials from local_remote.json file."""
        cred_path = get_base_path() / "credentials" / "local_remote.json"
        username = None
        password = None

        if cred_path.exists():
            try:
                with open(cred_path, "r", encoding="utf-8") as f:
                    creds = json.load(f)
                    username = creds.get("username")
                    password = creds.get("password")
            except Exception:
                logger.warning("Failed to load generic credentials for PSRemoting.")

        if username:
            logger.info("PSRemote: loaded credentials for user '%s'", username)
        else:
            logger.warning("PSRemote: No username found in credentials file.")

        return username, password

    def _create_facade(
        self, target_host: str, username: str | None, password: str | None
    ) -> PSRemotingFacade:
        """Create PS remoting facade for the target host (with supplied credentials)."""
        # For now we instantiate fresh; consider DI if reused broadly.
        return PSRemotingFacade()

    def _determine_service_type(self, svc_name: str, instance: str) -> tuple[str, str]:
        """Determine service type and instance based on service name."""
        svc_type = "Other"
        svc_instance = instance  # assume belongs to this instance mostly

        name_lower = svc_name.lower()
        if "sql" in name_lower and "agent" in name_lower:
            svc_type = "SQL Agent"
        elif "sql" in name_lower and "browser" in name_lower:
            svc_type = "SQL Browser"
            svc_instance = "(Shared)"
        elif "mssql" in name_lower:
            svc_type = "Database Engine"
        elif "writer" in name_lower:
            svc_type = "VSS Writer"
            svc_instance = "(Shared)"

        return svc_type, svc_instance

    def _evaluate_service_finding(
        self,
        account: str,
        state: str,
        start_mode: str
    ) -> tuple[str, str | None, str]:
        """Evaluate service configuration and return finding details."""
        acct_lower = account.lower().strip()
        status_lower = state.lower().strip()
        startup_lower = start_mode.lower().strip()

        non_compliant_accounts = {
            "nt authority\\system",
            "localsystem",
            "local service",
            "network service",
        }
        is_bad_account = acct_lower in non_compliant_accounts
        is_stopped_auto = (
            "auto" in startup_lower and "running" not in status_lower
        )

        is_issue = is_bad_account or is_stopped_auto
        finding_status = "WARN" if is_issue else "PASS"
        risk_level = "medium" if is_issue else None

        desc_parts = []
        if is_bad_account:
            desc_parts.append(f"running as '{account}'")
        if is_stopped_auto:
            desc_parts.append("Auto-start service is stopped")
        if not is_issue:
            desc_parts.append("Service configuration OK (via PowerShell)")

        description = "; ".join(desc_parts)

        return finding_status, risk_level, description

    def _collect_services_via_powershell(self) -> int:  # pylint: disable=too-many-locals
        """Collect services using PowerShell/WMI (fallback)."""
        try:
            # Load credentials and create executor
            username, password = self._load_credentials()
            target_host = (
                "127.0.0.1"
                if self.ctx.server_name.lower() in ("localhost", ".", "(local)")
                else self.ctx.server_name
            )
            facade = self._create_facade(target_host, username, password)
            # Use facade to run a data-collection script (placeholder; replace with real script)
            script = "Get-Service | Select-Object Name, DisplayName, Status, StartType, StartName | ConvertTo-Json -Compress"
            command_result = facade.run_command(
                target_host,
                script,
                {"windows_credentials": {"domain_admin": {"username": username, "password": password}}},
                prefer_method=None,
            )
            if not command_result.success:
                logger.error("PowerShell service collection failed: %s", command_result.stderr)
                return 0

            try:
                ps_services = json.loads(command_result.stdout) if command_result.stdout else []
            except Exception as e:  # pylint: disable=broad-except
                logger.error("Failed to parse service data: %s", e)
                return 0
            if not ps_services:
                logger.warning(
                    "PowerShell executed but returned no services. "
                    "Raw Output Sample: %s",
                    str(result.raw_output)[:500] if result.raw_output else "None",
                )
                if result.error:
                    logger.warning("PS Result Error: %s", result.error)
                return 0

            for svc in ps_services:
                svc_name = svc.get("name", "")
                start_mode = svc.get("start_mode", "")
                state = svc.get("state", "")
                account = svc.get("start_name", "")

                # Determine type and evaluate finding
                svc_type, svc_instance = self._determine_service_type(svc_name, instance)
                finding_status, risk_level, desc = self._evaluate_service_finding(
                    account, state, start_mode
                )

                self.writer.add_service(
                    server_name=self.ctx.server_name,
                    instance_name=svc_instance,
                    service_name=svc_name,
                    service_type=svc_type,
                    status=state,
                    startup_type=start_mode,
                    service_account=account,
                )

                entity_key = f"{self.ctx.server_name}|{svc_instance}|{svc_name}".lower()
                self.save_finding(
                    finding_type="service",
                    entity_name=svc_name,
                    status=finding_status,
                    risk_level=risk_level,
                    description=f"Service '{svc_name}': {desc}",
                    recommendation="Review service configuration",
                    entity_key=entity_key,
                )

            logger.info(
                "Collected %d services via PowerShell fallback.", len(ps_services)
            )
            return len(ps_services)

        except Exception as e:
            logger.error("PowerShell fallback crashed: %s", e, exc_info=True)
            return 0

    def _collect_client_protocols(self) -> int:
        """Collect client network protocol configuration."""
        try:
            protocols = self.conn.execute_query(self.prov.get_client_protocols())

            # Map detected protocols by name (case-insensitive)
            detected = {p.get("ProtocolName", "").lower(): p for p in protocols}

            # Standard set of protocols to report
            standard_protocols = ["Shared Memory", "TCP/IP", "Named Pipes", "VIA"]

            for name in standard_protocols:
                name_lower = name.lower()
                p_data = detected.get(name_lower)

                # If detected, use actual values. If not (manual), assume disabled (compliant)
                if p_data:
                    is_enabled = bool(p_data.get("IsEnabled", 0))
                    port = p_data.get("DefaultPort")
                    notes = p_data.get("Notes", "")
                    source = "Detected"
                else:
                    is_enabled = False  # Assume compliant if not detectable via T-SQL
                    port = None
                    notes = (
                        "Manual entry required"
                        if name_lower not in ("shared memory", "tcp/ip")
                        else ""
                    )
                    source = "Manual"

                self.writer.add_client_protocol(
                    server_name=self.ctx.server_name,
                    instance_name=self.ctx.instance_name,
                    protocol_name=name,
                    is_enabled=is_enabled,
                    port=port,
                    notes=notes,
                )

                # Build entity_key: server|instance|protocol
                entity_key = (
                    f"{self.ctx.server_name}|{self.ctx.instance_name}|{name}".lower()
                )

                # Enabled protocols need review (except Shared Memory/TCP/IP usually)
                # But we mark everything PASS by default as per "assumed compliant"
                finding_status = "PASS"
                risk_level = None

                # If we detected it enabled and it's risky (VIA/Named Pipes), WARN?
                # User said "assumed to be in a compliant state", so PASS default.
                # If actual detection finds enabled VIA, we should probably WARN.
                if is_enabled and name_lower in ("via", "named pipes"):
                    finding_status = "WARN"
                    risk_level = "medium"

                self.save_finding(
                    finding_type="protocol",
                    entity_name=name,
                    status=finding_status,
                    risk_level=risk_level,
                    description=(
                        f"Protocol '{name}' is {'enabled' if is_enabled else 'disabled'} "
                        f"({source})"
                    ),
                    recommendation=(
                        "Disable unused protocols" if finding_status == "WARN" else None
                    ),
                    entity_key=entity_key,
                )

            return len(standard_protocols)
        except Exception as e:
            logger.warning("Client protocols failed: %s", e)
            return 0

    def _process_linked_server(self, ls: dict, login_map: dict[str, list[dict]]) -> int:
        """Process a single linked server and its login mappings."""
        # FIXED: Query returns LinkedServerName, not ServerName
        ls_name = ls.get("LinkedServerName", "")
        # FIXED: Query returns Provider and Product, not ProviderName/ProductName
        provider = ls.get("Provider", "")
        product = ls.get("Product", "")
        data_source = ls.get("DataSource", "")
        is_rpc_out_enabled = bool(ls.get("RpcOutEnabled"))

        # Get login mappings for this linked server
        mappings = login_map.get(ls_name, [])
        count = 0

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
                        description=(
                            f"Linked server '{ls_name}' uses high-privilege "
                            f"remote login '{remote_login}'"
                        ),
                        recommendation=(
                            "Use least-privilege credentials for linked "
                            "server connections"
                        ),
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
                count += self._process_linked_server(ls, login_map)

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
                        entity_name=db_name,
                        status="FAIL",
                        risk_level="high",
                        description=f"Database '{db_name}' has no recent FULL backup",
                        recommendation="Ensure regular backup schedule is running",
                    )
                elif recovery_model == "FULL" and not last_log:
                    self.save_finding(
                        finding_type="backup",
                        entity_name=db_name,
                        status="WARN",
                        risk_level="medium",
                        description=(
                            f"Database '{db_name}' is in FULL recovery but has no LOG backups"
                        ),
                        recommendation=(
                            "Schedule transaction log backups or switch to SIMPLE recovery"
                        ),
                    )
            return len(backups)
        except Exception as e:
            logger.warning("Backups failed: %s", e)
            return 0
