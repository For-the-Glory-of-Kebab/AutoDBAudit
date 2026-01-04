"""
Command execution helper for PSRemotingFacade.

Responsible for selecting/ensuring a connection profile and running commands/scripts.
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Dict, Any, Optional, Tuple, cast

from ..connection_manager import PSRemotingConnectionManager
from ..credentials import CredentialHandler
from ..models import CommandResult, ConnectionMethod, ConnectionProfile, PSRemotingResult
from ..repository import PSRemotingRepository


class CommandExecutor:
    """Executes commands/scripts using established or freshly prepared PS remoting profiles."""

    def __init__(
        self,
        connection_manager: PSRemotingConnectionManager,
        repository: PSRemotingRepository,
    ) -> None:
        self.connection_manager = connection_manager
        self.repository = repository
        self.credential_handler = CredentialHandler()

    def run_command(
        self,
        server: str,
        command: str,
        credentials: Dict[str, Any],
        prefer_method: Optional[ConnectionMethod],
    ) -> CommandResult:
        """Execute a single PowerShell command on the target."""
        _ = prefer_method  # reserved for future method selection refinements
        start = time.time()
        profile, ps_result = self._ensure_connection_profile(server, credentials)
        if not profile or not ps_result or not ps_result.is_success():
            error = (
                ps_result.error_message
                if ps_result
                else "Unable to establish PS remoting session"
            )
            return CommandResult(
                success=False,
                stdout="",
                stderr=error or "",
                exit_code=1,
                duration_ms=int((time.time() - start) * 1000),
                method_used=None,
                revert_scripts_applied=list(ps_result.revert_scripts or []) if ps_result else [],
                troubleshooting=ps_result.troubleshooting_report if ps_result else None,
            )

        result = self._invoke_command(profile, credentials, command)
        duration_ms = int((time.time() - start) * 1000)
        method_used = {
            "auth_method": profile.auth_method,
            "protocol": profile.protocol,
            "port": profile.port,
            "credential_type": profile.credential_type,
            "connection_method": profile.connection_method,
        }
        return CommandResult(
            success=result.returncode == 0,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
            exit_code=result.returncode,
            duration_ms=duration_ms,
            method_used=method_used,
            revert_scripts_applied=cast(list[str], ps_result.revert_scripts or []),
            troubleshooting=ps_result.troubleshooting_report,
        )

    def run_script(
        self,
        server: str,
        script: str,
        credentials: Dict[str, Any],
        prefer_method: Optional[ConnectionMethod],
    ) -> CommandResult:
        """Execute a PowerShell script (inline content or file path) on the target."""
        if os.path.isfile(script):
            with open(script, "r", encoding="utf-8") as handle:
                script_content = handle.read()
        else:
            script_content = script
        wrapped = f"Invoke-Expression \"{script_content.replace('\"', '`\"')}\""
        return self.run_command(server, wrapped, credentials, prefer_method)

    def _ensure_connection_profile(
        self, server: str, credentials: Dict[str, Any]
    ) -> Tuple[Optional[ConnectionProfile], Optional[PSRemotingResult]]:
        """
        Try stored profile first; otherwise run full prepare to get a fresh session/profile.
        """
        stored = self.repository.get_connection_profile(server)
        if stored and stored.successful:
            return stored, PSRemotingResult(
                success=True,
                session=None,
                error_message=None,
                attempts_made=[],
                duration_ms=0,
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=[],
                successful_permutations=[],
            )

        ps_result = self.connection_manager.connect_to_server(
            server,
            credentials,
            allow_config=True,
        )
        session = ps_result.get_session() if ps_result.is_success() else None
        profile = session.connection_profile if session else None
        return profile, ps_result

    def _invoke_command(
        self,
        profile: ConnectionProfile,
        credentials: Dict[str, Any],
        command: str,
    ) -> subprocess.CompletedProcess:
        """Build and execute an Invoke-Command using the supplied profile and credentials."""
        bundle = self.credential_handler.prepare_credentials(credentials)
        ps_cred = self.credential_handler.create_pscredential(bundle)
        auth = profile.auth_method or "Default"
        port = profile.port or 5985
        protocol = (profile.protocol or "http").lower()
        use_ssl = "-UseSSL" if protocol == "https" else ""

        escaped_command = command.replace("'", "''")
        ps_parts = []
        if ps_cred:
            ps_parts.append(ps_cred)
            ps_parts.append("$cred = $credential")
        else:
            ps_parts.append("$cred = $null")

        ps_parts.append(
            "Invoke-Command "
            f"-ComputerName '{profile.server_name}' "
            f"-Authentication {auth} "
            f"-Port {port} "
            f"{use_ssl} "
            "-Credential $cred "
            "-ScriptBlock { param($c) Invoke-Expression $c } "
            f"-ArgumentList '{escaped_command}'"
        )

        ps_command = "\n".join(ps_parts)
        return subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
