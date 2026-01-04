# pylint: disable=line-too-long,too-many-arguments,too-many-positional-arguments
"""
Localhost preparation helper for PS remoting.

Isolates localhost-specific setup to keep the main connection manager focused on
remote orchestration.
"""

import subprocess
from typing import List, Callable

from .manual_support import (
    generate_manual_setup_scripts,
    generate_troubleshooting_report,
)
from .models import ConnectionAttempt, CredentialBundle, PSRemotingResult

class LocalhostPreparer:
    """Enables WinRM locally and retries direct connection attempts."""

    def __init__(
        self,
        is_windows: bool,
        direct_layer: Callable[[str, CredentialBundle, List[ConnectionAttempt], int], PSRemotingResult],
        timestamp_provider: Callable[[], str],
        repository,
        revert_scripts_provider: Callable[[], List[str]],
    ):
        self._is_windows = is_windows
        self._direct_layer = direct_layer
        self._timestamp = timestamp_provider
        self._repository = repository
        self._revert_scripts_provider = revert_scripts_provider

    def prepare_and_validate(
        self,
        server_name: str,
        bundle: CredentialBundle,
        _start_time: float,
        profile_id: int,
    ) -> PSRemotingResult:
        """Enable localhost remoting and attempt connection."""
        if not self._is_windows:
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="Localhost preparation only supported on Windows",
                attempts_made=[],
                duration_ms=0,
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=[],
            )

        self._enable_localhost_winrm()
        attempts: List[ConnectionAttempt] = []
        result = self._direct_layer(server_name, bundle, attempts, profile_id)
        if result.is_success():
            self._repository.log_attempts(attempts, profile_id=profile_id)
            return result

        manual_report = generate_troubleshooting_report(
            server_name, attempts, self._timestamp
        )
        manual_scripts = generate_manual_setup_scripts(server_name)
        self._repository.log_attempts(attempts, profile_id=profile_id)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Localhost PS remoting setup failed",
            attempts_made=attempts,
            duration_ms=0,
            troubleshooting_report=manual_report,
            manual_setup_scripts=manual_scripts,
            revert_scripts=self._revert_scripts_provider(),
        )

    @staticmethod
    def _enable_localhost_winrm() -> None:
        """Enable WinRM and firewall locally for localhost testing."""
        setup_commands = [
            "Enable-PSRemoting -Force -SkipNetworkProfileCheck",
            "Set-Service -Name WinRM -StartupType Automatic",
            "Start-Service -Name WinRM",
            "Enable-NetFirewallRule -DisplayGroup \"Windows Remote Management\"",
            (
                "New-ItemProperty -Path "
                "'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' "
                "-Name 'LocalAccountTokenFilterPolicy' -Value 1 -PropertyType DWORD -Force"
            ),
            (
                "New-ItemProperty -Path "
                "'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa' "
                "-Name 'DisableLoopbackCheck' -Value 1 -PropertyType DWORD -Force"
            ),
        ]

        for command in setup_commands:
            subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
