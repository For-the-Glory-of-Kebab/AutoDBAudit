"""
Script Executor - Remote PowerShell Script Runner.

Executes PowerShell scripts on remote hosts via PSRemote.
Handles JSON result parsing and error recovery.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from autodbaudit.infrastructure.psremote.client import (
    PSRemoteClient,
    ConnectionConfig,
)

logger = logging.getLogger(__name__)

# Path to bundled scripts
SCRIPTS_DIR = Path(__file__).parent.parent.parent.parent.parent / "assets" / "scripts"


@dataclass
class ExecutionResult:
    """Result from script execution."""

    success: bool
    data: dict[str, Any] | None = None
    raw_output: str = ""
    error: str = ""
    script_name: str = ""
    connection_info: dict[str, str] = field(default_factory=dict)


class ScriptExecutor:
    """
    Executes bundled PowerShell scripts on remote hosts.

    Wraps PSRemoteClient with script-specific logic:
    - Reads script from assets/scripts/
    - Injects parameters
    - Parses JSON output
    - Handles errors gracefully
    """

    def __init__(self, client: PSRemoteClient) -> None:
        """Initialize with PSRemote client."""
        self.client = client

    @classmethod
    def from_config(
        cls,
        hostname: str,
        username: str | None = None,
        password: str | None = None,
    ) -> ScriptExecutor:
        """Create executor from connection parameters."""
        config = ConnectionConfig(
            hostname=hostname,
            username=username,
            password=password,
        )
        client = PSRemoteClient(config)
        return cls(client)

    def get_os_data(self, instance_name: str = "MSSQLSERVER") -> ExecutionResult:
        """
        Execute Get-SqlServerOSData.ps1 remotely.

        Args:
            instance_name: SQL Server instance name

        Returns:
            ExecutionResult with parsed OS data
        """
        script_path = SCRIPTS_DIR / "Get-SqlServerOSData.ps1"

        if not script_path.exists():
            return ExecutionResult(
                success=False,
                error=f"Script not found: {script_path}",
                script_name="Get-SqlServerOSData.ps1",
            )

        # Read and parameterize script
        script_content = script_path.read_text(encoding="utf-8")

        # Create wrapper that sets parameter and runs
        wrapper = f"""
$InstanceName = '{instance_name}'
{script_content}
"""

        return self._execute_json_script(wrapper, "Get-SqlServerOSData.ps1")

    def restart_sql_service(
        self,
        instance_name: str = "MSSQLSERVER",
        stop_timeout: int = 60,
        start_timeout: int = 120,
    ) -> ExecutionResult:
        """
        Execute Restart-SqlServerService.ps1 remotely.

        Args:
            instance_name: SQL Server instance name
            stop_timeout: Seconds to wait for stop
            start_timeout: Seconds to wait for start

        Returns:
            ExecutionResult with restart status
        """
        script_path = SCRIPTS_DIR / "Restart-SqlServerService.ps1"

        if not script_path.exists():
            return ExecutionResult(
                success=False,
                error=f"Script not found: {script_path}",
                script_name="Restart-SqlServerService.ps1",
            )

        script_content = script_path.read_text(encoding="utf-8")

        wrapper = f"""
$InstanceName = '{instance_name}'
$StopTimeoutSeconds = {stop_timeout}
$StartTimeoutSeconds = {start_timeout}
{script_content}
"""

        return self._execute_json_script(wrapper, "Restart-SqlServerService.ps1")

    def set_client_protocol(
        self,
        instance_name: str,
        protocol: str,
        enabled: bool,
    ) -> ExecutionResult:
        """
        Execute Set-ClientProtocol.ps1 remotely.

        Args:
            instance_name: SQL Server instance name
            protocol: Protocol name (Tcp, Np, Sm, Via)
            enabled: Whether to enable or disable

        Returns:
            ExecutionResult with protocol change status
        """
        script_path = SCRIPTS_DIR / "Set-ClientProtocol.ps1"

        if not script_path.exists():
            return ExecutionResult(
                success=False,
                error=f"Script not found: {script_path}",
                script_name="Set-ClientProtocol.ps1",
            )

        script_content = script_path.read_text(encoding="utf-8")
        enabled_str = "$true" if enabled else "$false"

        wrapper = f"""
$InstanceName = '{instance_name}'
$Protocol = '{protocol}'
$Enabled = {enabled_str}
{script_content}
"""

        return self._execute_json_script(wrapper, "Set-ClientProtocol.ps1")

    def run_custom_script(
        self, script_content: str, script_name: str = "custom"
    ) -> ExecutionResult:
        """
        Run custom PowerShell script.

        Args:
            script_content: PowerShell script content
            script_name: Name for logging

        Returns:
            ExecutionResult with output
        """
        result = self.client.run_ps(script_content)

        return ExecutionResult(
            success=result.success,
            raw_output=result.stdout,
            error=result.stderr if not result.success else "",
            script_name=script_name,
            connection_info={
                "transport": result.transport_used,
                "auth": result.auth_used,
            },
        )

    def _execute_json_script(self, script: str, script_name: str) -> ExecutionResult:
        """Execute script and parse JSON output."""
        result = self.client.run_ps(script)

        if not result.success:
            return ExecutionResult(
                success=False,
                raw_output=result.stdout,
                error=result.stderr or result.error,
                script_name=script_name,
                connection_info={
                    "transport": result.transport_used,
                    "auth": result.auth_used,
                },
            )

        # Try to parse JSON from output
        try:
            # Find JSON in output (may have other text before/after)
            output = result.stdout.strip()
            json_start = output.find("{")
            json_end = output.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = output[json_start:json_end]
                data = json.loads(json_str)

                return ExecutionResult(
                    success=data.get("success", True),
                    data=data,
                    raw_output=result.stdout,
                    error=data.get("error", ""),
                    script_name=script_name,
                    connection_info={
                        "transport": result.transport_used,
                        "auth": result.auth_used,
                    },
                )
            else:
                # No JSON found, return raw output
                return ExecutionResult(
                    success=True,
                    raw_output=result.stdout,
                    script_name=script_name,
                    connection_info={
                        "transport": result.transport_used,
                        "auth": result.auth_used,
                    },
                )

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON from %s: %s", script_name, e)
            return ExecutionResult(
                success=True,  # Script ran, just couldn't parse
                raw_output=result.stdout,
                error=f"JSON parse error: {e}",
                script_name=script_name,
                connection_info={
                    "transport": result.transport_used,
                    "auth": result.auth_used,
                },
            )

    def close(self) -> None:
        """Close the underlying client."""
        self.client.close()
