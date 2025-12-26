"""
Collector for Server Instance Properties and Version Compliance.
"""

from __future__ import annotations

import logging
from autodbaudit.application.collectors.base import BaseCollector
from autodbaudit.infrastructure.excel.base import get_sql_year

logger = logging.getLogger(__name__)


class ServerPropertiesCollector(BaseCollector):
    """
    Collects high-level server and instance properties.
    Performs version compliance checks.
    """

    def collect(self, config_name: str, config_ip: str) -> int:
        """
        Collect instance properties.
        Returns 1 if successful, 0 otherwise.
        """
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
                config_name=config_name or self.ctx.server_name,
                server_name=self.ctx.server_name,
                instance_name=self.ctx.instance_name,
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
                sql_year = get_sql_year(version_major)
                expected = (
                    self.ctx.expected_builds.get(sql_year, "unknown")
                    if self.ctx.expected_builds
                    else "unknown"
                )

                self.save_finding(
                    finding_type="version",
                    entity_name=f"sql_version_{sql_year}",
                    status="WARN",
                    risk_level="medium",
                    description=f"SQL {sql_year} at {version}, expected {expected}",
                    recommendation=f"Update to SQL Server {sql_year} build {expected}",
                )

            # Instance naming check - default instance is a security risk
            # (Requirement 14: No SQL instance should use the default instance name)
            # EXCEPTION: Docker/Linux SQL Server cannot use named instances
            instance_name = self.ctx.instance_name or ""
            is_default_instance = (
                instance_name.upper() in ("MSSQLSERVER", "(DEFAULT)", "")
                or not instance_name
            )

            # Check if this is Linux/Docker (default instance is expected and OK)
            is_linux = "linux" in os_info.lower() or "ubuntu" in os_info.lower()
            is_container = "container" in os_info.lower() or os_platform == "Linux"

            if is_default_instance and not (is_linux or is_container):
                self.save_finding(
                    finding_type="instance_naming",
                    entity_name="default_instance_name",
                    status="WARN",
                    risk_level="medium",
                    description=(
                        "SQL Server is using the default instance name (MSSQLSERVER). "
                        "Default instances are easier targets for attackers."
                    ),
                    recommendation=(
                        "Consider migrating to a named instance. Note: This requires "
                        "reinstallation on a named instance and data migration. "
                        "Cannot be automated."
                    ),
                )

            return 1
        except Exception as e:
            logger.warning("Instance properties failed: %s", e)
            return 0

    def _check_version_compliance(
        self, version: str, version_major: int
    ) -> tuple[str, str]:
        """
        Check if SQL Server version matches expected build from context.
        Returns: (status, note)
        """
        sql_year = get_sql_year(version_major)

        # If no expected builds configured, assume current
        if not self.ctx.expected_builds:
            return "PASS", ""

        # Check if this major version has an expected build
        expected = self.ctx.expected_builds.get(sql_year)
        if not expected:
            # No expectation for this version = assume current
            return "PASS", ""

        # Compare versions
        if version == expected:
            return "PASS", f"At expected build {expected}"

        # Version mismatch - show update available
        return "WARN", f"Current: {version}, Expected: {expected}"
