"""
PS Remoting Connection Manager

Core connection engine implementing comprehensive 5-layer resilient connection strategy.
Handles all Windows management hurdles: firewall, services, registry, GPO, WMI, SSH fallbacks.
Provides complete revert capabilities for all configuration changes.
"""

import time
import subprocess
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
import platform
import ipaddress

from .config.client_config import ClientConfigurator
from .config.target_config import TargetConfigurator
from .layers.direct_runner import DirectAttemptRunner
from .layers.layer2_client import ClientLayerRunner
from .layers.layer3_target import TargetLayerRunner
from .layers.revert_tracker import RevertTracker

from .models import (
    ConnectionProfile,
    ConnectionAttempt,
    PSRemotingResult,
    CredentialBundle,
    ConnectionMethod,
)
from .credentials import CredentialHandler
from .layers.fallbacks import (
    try_psexec_connection,
    try_rpc_connection,
    try_ssh_powershell,
    try_wmi_connection,
)
from .repository import PSRemotingRepository
from .elevation import ShellElevationService
from .layers.manual_layer import run_manual_layer
from .layers.localhost_prep import LocalhostPreparer

logger = logging.getLogger(__name__)
# pylint: disable=too-many-instance-attributes,too-many-branches,too-many-return-statements,line-too-long,too-many-statements

class PSRemotingConnectionManager:
    """
    Comprehensive PS remoting connection manager with full Windows management capabilities.

    Implements resilient 5-layer connection strategy with complete hurdle management:

    Layer 1: Direct connection attempts (all auth methods, ports, protocols)
    Layer 2: Client-side configuration (TrustedHosts, WinRM client settings)
    Layer 3: Target configuration (WinRM service, firewall, listeners, registry)
    Layer 4: Advanced fallbacks (SSH, WMI, psexec, RPC)
    Layer 5: Manual override with detailed logging and revert scripts

    Manages all Windows hurdles:
    - Firewall rules (WinRM HTTP/HTTPS exceptions)
    - WinRM service (start/enable/automatic startup)
    - Registry settings (LocalAccountTokenFilterPolicy, DisableLoopbackCheck)
    - TrustedHosts management
    - WinRM listeners (HTTP/HTTPS creation)
    - Authentication method exhaustion
    - GPO restriction handling
    - WMI/RPC fallbacks for WinRM failures
    - SSH/Samba alternatives
    - Complete revert capabilities
    """

    def __init__(self, repository: Optional[PSRemotingRepository] = None):
        self.repository: PSRemotingRepository = repository or PSRemotingRepository()
        self.credential_handler: CredentialHandler = CredentialHandler()
        self.client_config: ClientConfigurator = ClientConfigurator()
        self.target_config: TargetConfigurator = TargetConfigurator()
        self._is_windows = platform.system() == "Windows"
        self.revert_tracker: RevertTracker = RevertTracker(self._get_timestamp)
        self.direct_runner: DirectAttemptRunner = DirectAttemptRunner(
            self.credential_handler,
            self._get_timestamp,
            self._is_windows
        )
        self.client_layer: ClientLayerRunner = ClientLayerRunner(
            self.client_config,
            self.direct_runner,
            self._is_windows,
            self.revert_tracker.add_revert_script
        )
        self.target_layer: TargetLayerRunner = TargetLayerRunner(
            self.target_config,
            self.revert_tracker,
            self.direct_runner,
            self._is_ip_address,
            self._has_admin_credentials,
            self._execute_ps_command_with_creds
        )
        self._elevation_service = ShellElevationService()
        self.localhost_preparer = LocalhostPreparer(
            self._is_windows,
            self._layer1_direct_attempts,
            self._get_timestamp,
            self.repository,
            lambda: self.revert_tracker.scripts
        )

    def connect_to_server(self, server_name: str, credentials: Dict[str, Any],
                          allow_config: bool = True) -> PSRemotingResult:
        """
        Establish PS remoting connection using comprehensive resilient strategy.

        Args:
            server_name: Target server hostname or IP
            credentials: Credential configuration
            allow_config: Whether to allow configuration changes

        Returns:
            PSRemotingResult: Connection result with success/failure details
        """
        start_time = time.time()
        attempts: List[ConnectionAttempt] = []
        self.revert_tracker.reset()

        is_elevated = not self._is_windows or self._elevation_service.is_shell_elevated()
        allow_config_effective = allow_config and is_elevated
        if allow_config and not is_elevated:
            logger.warning(
                "Elevation required for configuration steps; proceeding with connection-only attempts."
            )

        # Prepare credentials
        credential_bundle = self.credential_handler.prepare_credentials(credentials)
        profile_id = self.repository.ensure_profile(server_name)

        # Localhost preparation shortcut
        if self._is_localhost(server_name):
            result = self.localhost_preparer.prepare_and_validate(
                server_name,
                credential_bundle,
                start_time,
                profile_id
            )
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        # Try stored profile first if available
        stored_profile = self.repository.get_connection_profile(server_name)
        if stored_profile:
            result = self._try_stored_profile(stored_profile, credential_bundle, attempts, profile_id)
            if result.is_success():
                self.repository.log_attempts(attempts, profile_id=stored_profile.id if hasattr(stored_profile, "id") else None)
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 1: Direct connection attempts
        result = self._layer1_direct_attempts(server_name, credential_bundle, attempts, profile_id)
        if result.is_success():
            session = result.get_session()
            if session:
                saved_id = self._save_successful_profile(session.connection_profile)
                self.repository.log_attempts(attempts, profile_id=saved_id)
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        # Reverse DNS retry for IP targets
        if self._is_ip_address(server_name):
            alt_host = self.direct_runner.reverse_dns(server_name)
            if alt_host and alt_host.lower() != server_name.lower():
                logger.info("Reverse DNS resolved %s -> %s. Retrying direct attempts.", server_name, alt_host)
                result = self._layer1_direct_attempts(alt_host, credential_bundle, attempts, profile_id)
                if result.is_success():
                    session = result.get_session()
                    if session:
                        saved_id = self._save_successful_profile(session.connection_profile)
                        self.repository.log_attempts(attempts, profile_id=saved_id)
                    result.duration_ms = int((time.time() - start_time) * 1000)
                    return result

        # Layer 2: Client-side configuration (if allowed)
        if allow_config_effective:
            result = self._layer2_client_config(server_name, credential_bundle, attempts, profile_id)
            if result.is_success():
                session = result.get_session()
                if session:
                    saved_id = self._save_successful_profile(session.connection_profile)
                    self.repository.log_attempts(attempts, profile_id=saved_id)
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 3: Target configuration (if allowed)
        if allow_config_effective:
            result = self._layer3_target_config(server_name, credential_bundle, attempts, profile_id)
            if result.is_success():
                session = result.get_session()
                if session:
                    saved_id = self._save_successful_profile(session.connection_profile)
                    self.repository.log_attempts(attempts, profile_id=saved_id)
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 4: Advanced fallbacks
        if allow_config_effective:
            result = self._layer4_advanced_fallbacks(server_name, credential_bundle, attempts, profile_id)
            if result.is_success():
                session = result.get_session()
                if session:
                    saved_id = self._save_successful_profile(session.connection_profile)
                    self.repository.log_attempts(attempts, profile_id=saved_id)
                else:
                    # Persist fallback success details even without a PSSession
                    saved_id = self._save_profile_from_attempt(attempts[-1], profile_id, server_name)
                    self.repository.log_attempts(attempts, profile_id=saved_id)
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 5: Manual override and detailed logging
        result = run_manual_layer(server_name, attempts, self._get_timestamp, self.revert_tracker.scripts)
        result.duration_ms = int((time.time() - start_time) * 1000)
        self.repository.log_attempts(attempts, profile_id=profile_id)
        return result

    def _try_stored_profile(self, profile: ConnectionProfile,
                           bundle: CredentialBundle,
                           attempts: List[ConnectionAttempt],
                           profile_id: int) -> PSRemotingResult:
        """Try connecting using a stored successful profile."""
        attempt = ConnectionAttempt(
            profile_id=profile_id,
            server_name=profile.server_name,
            auth_method=profile.auth_method,
            protocol=profile.protocol,
            port=profile.port,
            credential_type=self._credential_to_str(self.credential_handler.get_credential_type(bundle)),
            error_message=None,
            attempted_at=self._get_timestamp(),
            attempt_timestamp=self._get_timestamp(),
            layer="stored_profile",
            connection_method=profile.connection_method,
            created_at=self._get_timestamp(),
            duration_ms=0,
            config_changes=None,
            rollback_actions=None,
            manual_script_path=None
        )
        attempt.profile_id = profile_id

        try:
            session = self.direct_runner.connect_with_profile(profile, bundle)
            if session:
                attempt.duration_ms = 100  # Minimal duration for stored profile
                attempt.success = True
                attempts.append(attempt)
                return PSRemotingResult(
                    success=True,
                    session=session,
                    attempts_made=attempts,
                    error_message=None,
                    duration_ms=attempt.duration_ms or 0,
                    troubleshooting_report=None,
                    manual_setup_scripts=None,
                    revert_scripts=self.revert_tracker.scripts
                )
        except Exception as e:
            attempt.error_message = str(e)
            attempt.duration_ms = 100

        attempts.append(attempt)
        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Stored profile failed",
            attempts_made=attempts,
            duration_ms=attempt.duration_ms or 0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=self.revert_tracker.scripts
        )

    def _layer1_direct_attempts(self, server_name: str,
                               bundle: CredentialBundle,
                               attempts: List[ConnectionAttempt],
                               profile_id: int) -> PSRemotingResult:
        """Layer 1: Try all possible direct connection methods."""
        return self.direct_runner.layer1_direct_attempts(
            server_name,
            bundle,
            attempts,
            profile_id
        )

    def _layer2_client_config(self, server_name: str,
                            bundle: CredentialBundle,
                            attempts: List[ConnectionAttempt],
                            profile_id: int) -> PSRemotingResult:
        """Layer 2: Apply client-side configuration changes."""
        return self.client_layer.run(
            server_name,
            bundle,
            attempts,
            profile_id
        )

    def _layer3_target_config(self, server_name: str,
                            bundle: CredentialBundle,
                            attempts: List[ConnectionAttempt],
                            profile_id: int) -> PSRemotingResult:
        """
        Layer 3: Comprehensive target server configuration.

        Applies all necessary configuration changes to target server:
        - WinRM service management (start/enable/automatic)
        - Firewall rules (WinRM HTTP/HTTPS exceptions)
        - Registry settings (LocalAccountTokenFilterPolicy, DisableLoopbackCheck)
        - WinRM listeners (HTTP/HTTPS creation)
        - TrustedHosts on target (for IP-based connections)
        """
        logger.info("Layer 3: Configuring target server %s", server_name)
        return self.target_layer.run(
            server_name,
            bundle,
            attempts,
            profile_id
        )

    def _layer4_advanced_fallbacks(self, server_name: str,
                                  bundle: CredentialBundle,
                                  attempts: List[ConnectionAttempt],
                                  profile_id: int) -> PSRemotingResult:
        """
        Layer 4: Advanced fallback connection methods.

        When WinRM fails completely, try alternative approaches:
        - SSH-based PowerShell (if OpenSSH available)
        - WMI/RPC connections
        - psexec for command execution
        - Direct SMB/CIFS access
        """
        logger.info("Layer 4: Trying advanced fallbacks for %s", server_name)

        # Try SSH-based PowerShell
        result = try_ssh_powershell(
            server_name,
            bundle,
            attempts,
            self.credential_handler,
            self._get_timestamp
        )
        if result.is_success():
            self.repository.log_attempts(attempts, profile_id=profile_id)
            return result

        # Try WMI connections
        result = try_wmi_connection(
            server_name,
            bundle,
            attempts,
            self.credential_handler,
            self._get_timestamp
        )
        if result.is_success():
            self.repository.log_attempts(attempts, profile_id=profile_id)
            return result

        # Try psexec fallback
        result = try_psexec_connection(
            server_name,
            bundle,
            attempts,
            self.credential_handler,
            self._get_timestamp
        )
        if result.is_success():
            self.repository.log_attempts(attempts, profile_id=profile_id)
            return result

        # Try RPC connections
        result = try_rpc_connection(
            server_name,
            bundle,
            attempts,
            self.credential_handler,
            self._get_timestamp
        )
        if result.is_success():
            self.repository.log_attempts(attempts, profile_id=profile_id)
            return result

        final_result = PSRemotingResult(
            success=False,
            session=None,
            error_message="Layer 4: All advanced fallbacks failed",
            attempts_made=attempts,
            duration_ms=0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=self.revert_tracker.scripts
        )
        self.repository.log_attempts(attempts, profile_id=profile_id)
        return final_result

    def _save_successful_profile(self, profile: ConnectionProfile):
        """Save successful connection profile."""
        timestamp = self._get_timestamp()
        updated_profile = profile.model_copy(
            update={
                "last_successful_attempt": timestamp,
                "last_attempt": timestamp,
                "updated_at": timestamp,
                "successful": True,
            }
        )
        profile_id = self.repository.save_connection_profile(updated_profile)
        return profile_id

    def _save_profile_from_attempt(
        self,
        attempt: ConnectionAttempt,
        profile_id: Optional[int],
        server_name: str,
    ) -> int:
        """Persist a connection profile derived from a successful attempt (e.g., fallback)."""
        timestamp = self._get_timestamp()
        profile = ConnectionProfile(
            id=profile_id,
            server_name=server_name,
            connection_method=attempt.connection_method or ConnectionMethod.POWERSHELL_REMOTING,
            auth_method=attempt.auth_method,
            protocol=attempt.protocol,
            port=attempt.port,
            credential_type=attempt.credential_type,
            successful=True,
            last_successful_attempt=timestamp,
            last_attempt=timestamp,
            attempt_count=1,
            sql_targets=[],
            baseline_state=None,
            current_state=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        return self.repository.save_connection_profile(profile)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()

    def revert_server(
        self,
        server_name: str,
        credentials: Dict[str, Any],
        dry_run: bool = False
    ) -> PSRemotingResult:
        """
        Revert PS remoting changes on a target server.

        Generates and executes a revert script to undo firewall, service,
        and registry modifications. Returns the script for audit/manual use.
        """
        start_time = time.time()
        if not self._is_windows:
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="Revert supported on Windows clients only",
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=[]
            )

        bundle = self.credential_handler.prepare_credentials(credentials)
        revert_script = self._build_revert_script(server_name)
        client_cleanup = self._build_client_trustedhosts_cleanup(server_name)
        scripts = [revert_script, client_cleanup]

        if dry_run:
            return PSRemotingResult(
                success=True,
                session=None,
                error_message=None,
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=scripts
            )

        try:
            result = self._execute_ps_command_with_creds(revert_script, bundle)
            client_result = subprocess.run(
                ["powershell", "-Command", client_cleanup],
                capture_output=True,
                text=True,
                timeout=20,
                check=False
            )

            success = result.returncode == 0 and client_result.returncode == 0
            error = None
            if not success:
                error = "\n".join([result.stderr or "", client_result.stderr or ""]).strip()

            return PSRemotingResult(
                success=success,
                session=None,
                error_message=error if not success else None,
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=scripts
            )
        except Exception as exc:
            return PSRemotingResult(
                success=False,
                session=None,
                error_message=str(exc),
                attempts_made=[],
                duration_ms=int((time.time() - start_time) * 1000),
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=scripts
            )

    def _build_revert_script(self, server_name: str) -> str:
        """PowerShell script to revert target-side changes."""
        return f"""
        Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
            Write-Host "Reverting WinRM configuration on {server_name}"

            # Stop and disable WinRM service
            Stop-Service -Name WinRM -ErrorAction SilentlyContinue
            Set-Service -Name WinRM -StartupType Manual -ErrorAction SilentlyContinue

            # Remove WinRM firewall rules
            Get-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
            Get-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue

            # Remove registry overrides if present
            Remove-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue
            Remove-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" -Name "DisableLoopbackCheck" -ErrorAction SilentlyContinue

            Write-Host "Revert complete on {server_name}"
        }}
        """

    def _build_client_trustedhosts_cleanup(self, server_name: str) -> str:
        """PowerShell to remove a server entry from client TrustedHosts."""
        return self.client_config.cleanup_trustedhosts(server_name)

    def test_connection(self, server_name: str, credentials: Dict[str, Any]) -> bool:
        """
        Quick test if connection is possible.

        Args:
            server_name: Server to test
            credentials: Credentials to use

        Returns:
            bool: True if connection test passes
        """
        result = self.connect_to_server(server_name, credentials, allow_config=False)
        return result.is_success()

    # Helper methods

    def _execute_ps_command_with_creds(
        self,
        script: str,
        bundle: CredentialBundle
    ) -> subprocess.CompletedProcess:
        """Execute PowerShell command with credentials."""
        # This is a simplified implementation
        # In practice, you'd need to securely pass credentials
        ps_cred = self.credential_handler.create_pscredential(bundle)
        if ps_cred:
            script = script.replace("(Get-Credential)", f"({ps_cred})")

        return subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            check=False
        )

    @staticmethod
    def _has_admin_credentials(bundle: CredentialBundle) -> bool:
        """
        Simple admin heuristic: credentials are present.
        Real implementation should validate group membership/privilege.
        """
        if bundle.windows_explicit:
            username = bundle.windows_explicit.get("username")
            password = bundle.windows_explicit.get("password")
            return bool(username and password)
        return False

    @staticmethod
    def _credential_to_str(value) -> Optional[str]:
        """Normalize credential type to string for persistence."""
        if value is None:
            return None
        return value.value if hasattr(value, "value") else str(value)

    def _is_ip_address(self, hostname: str) -> bool:
        """Check if hostname is an IP address."""
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    @staticmethod
    def _is_localhost(server_name: str) -> bool:
        """Determine if the target refers to localhost."""
        normalized = server_name.strip().lower()
        return normalized in {"localhost", "127.0.0.1", "::1"}
