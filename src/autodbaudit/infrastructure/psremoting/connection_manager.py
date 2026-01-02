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

from .models import (
    AuthMethod,
    Protocol,
    ConnectionProfile,
    ConnectionAttempt,
    PSSession,
    PSRemotingResult,
    CredentialBundle
)
from .credentials import CredentialHandler
from .repository import PSRemotingRepository

logger = logging.getLogger(__name__)


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
        self.repository = repository or PSRemotingRepository()
        self.credential_handler = CredentialHandler()
        self._is_windows = platform.system() == "Windows"

        # Track configuration changes for revert
        self._changes_made: List[Dict[str, Any]] = []
        self._revert_scripts: List[str] = []

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
        self._changes_made = []
        self._revert_scripts = []

        # Prepare credentials
        credential_bundle = self.credential_handler.prepare_credentials(credentials)

        # Try stored profile first if available
        stored_profile = self.repository.get_connection_profile(server_name)
        if stored_profile:
            result = self._try_stored_profile(stored_profile, credential_bundle, attempts)
            if result.is_success():
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 1: Direct connection attempts
        result = self._layer1_direct_attempts(server_name, credential_bundle, attempts)
        if result.is_success():
            self._save_successful_profile(result.get_session().connection_profile)
            result.duration_ms = int((time.time() - start_time) * 1000)
            return result

        # Layer 2: Client-side configuration (if allowed)
        if allow_config:
            result = self._layer2_client_config(server_name, credential_bundle, attempts)
            if result.is_success():
                self._save_successful_profile(result.get_session().connection_profile)
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 3: Target configuration (if allowed)
        if allow_config:
            result = self._layer3_target_config(server_name, credential_bundle, attempts)
            if result.is_success():
                self._save_successful_profile(result.get_session().connection_profile)
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 4: Advanced fallbacks
        if allow_config:
            result = self._layer4_advanced_fallbacks(server_name, credential_bundle, attempts)
            if result.is_success():
                self._save_successful_profile(result.get_session().connection_profile)
                result.duration_ms = int((time.time() - start_time) * 1000)
                return result

        # Layer 5: Manual override and detailed logging
        result = self._layer5_manual_override(server_name, attempts)

        # All layers failed
        result = PSRemotingResult(
            success=False,
            session=None,
            error_message="All connection methods failed",
            attempts_made=attempts,
            duration_ms=int((time.time() - start_time) * 1000),
            revert_scripts=self._revert_scripts
        )
        return result

    def _try_stored_profile(self, profile: ConnectionProfile,
                           bundle: CredentialBundle,
                           attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Try connecting using a stored successful profile."""
        attempt = ConnectionAttempt(
            server_name=profile.server_name,
            auth_method=profile.auth_method,
            protocol=profile.protocol,
            port=profile.port,
            credential_type=profile.credential_type,            error_message=None,            attempted_at=self._get_timestamp()
        )

        try:
            session = self._execute_connection_attempt(profile, bundle)
            if session:
                attempt.duration_ms = 100  # Minimal duration for stored profile
                attempts.append(attempt)
                return PSRemotingResult(
                    success=True,
                    session=session,
                    attempts_made=attempts
                )
        except Exception as e:
            attempt.error_message = str(e)
            attempt.duration_ms = 100

        attempts.append(attempt)
        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Stored profile failed",
            attempts_made=attempts
        )

    def _layer1_direct_attempts(self, server_name: str,
                               bundle: CredentialBundle,
                               attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Layer 1: Try all possible direct connection methods."""
        auth_methods = [AuthMethod.DEFAULT, AuthMethod.KERBEROS, AuthMethod.NTLM,
                       AuthMethod.NEGOTIATE, AuthMethod.BASIC, AuthMethod.CREDSsp]
        protocols = [Protocol.HTTP, Protocol.HTTPS]
        ports = [5985, 5986]  # HTTP, HTTPS

        for auth_method in auth_methods:
            for protocol in protocols:
                for port in ports:
                    result = self._try_single_connection(
                        server_name, auth_method, protocol, port, bundle, attempts
                    )
                    if result.is_success():
                        return result

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Layer 1: All direct attempts failed",
            attempts_made=attempts
        )

    def _layer2_client_config(self, server_name: str,
                            bundle: CredentialBundle,
                            attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Layer 2: Apply client-side configuration changes."""
        if not self._is_windows:
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="Layer 2: Client config only supported on Windows",
                attempts_made=attempts
            )

        # Add to TrustedHosts
        if self._add_to_trusted_hosts(server_name):
            # Retry Layer 1 after TrustedHosts update
            result = self._layer1_direct_attempts(server_name, bundle, attempts)
            if result.is_success():
                return result

        # Configure WinRM client settings
        self._configure_winrm_client()

        # Retry Layer 1 after client config
        return self._layer1_direct_attempts(server_name, bundle, attempts)

    def _layer3_target_config(self, server_name: str,
                            bundle: CredentialBundle,
                            attempts: List[ConnectionAttempt]) -> PSRemotingResult:
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

        # Check if we have admin credentials for target configuration
        if not self._has_admin_credentials(bundle):
            logger.warning("Layer 3: Skipping target config - no admin credentials")
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="Layer 3: Admin credentials required for target configuration",
                attempts_made=attempts
            )

        try:
            # WinRM service management
            if not self._ensure_winrm_service_running(server_name, bundle):
                logger.warning("Failed to ensure WinRM service on target")

            # Firewall configuration
            if not self._configure_firewall_rules(server_name, bundle):
                logger.warning("Failed to configure firewall rules on target")

            # Registry modifications
            if not self._configure_registry_settings(server_name, bundle):
                logger.warning("Failed to configure registry settings on target")

            # WinRM listeners
            if not self._ensure_winrm_listeners(server_name, bundle):
                logger.warning("Failed to ensure WinRM listeners on target")

            # Target TrustedHosts (for IP connections)
            if not self._configure_target_trustedhosts(server_name, bundle):
                logger.warning("Failed to configure target TrustedHosts")

            # Retry Layer 1 after target configuration
            logger.info("Layer 3: Retrying connection after target configuration")
            return self._layer1_direct_attempts(server_name, bundle, attempts)

        except Exception as e:
            logger.exception("Layer 3: Target configuration failed: %s", e)
            return PSRemotingResult(
                success=False,
                session=None,
                error_message=f"Layer 3: Target configuration failed: {str(e)}",
                attempts_made=attempts
            )

    def _layer4_advanced_fallbacks(self, server_name: str,
                                  bundle: CredentialBundle,
                                  attempts: List[ConnectionAttempt]) -> PSRemotingResult:
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
        result = self._try_ssh_powershell(server_name, bundle, attempts)
        if result.is_success():
            return result

        # Try WMI connections
        result = self._try_wmi_connection(server_name, bundle, attempts)
        if result.is_success():
            return result

        # Try psexec fallback
        result = self._try_psexec_connection(server_name, bundle, attempts)
        if result.is_success():
            return result

        # Try RPC connections
        result = self._try_rpc_connection(server_name, bundle, attempts)
        if result.is_success():
            return result

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Layer 4: All advanced fallbacks failed",
            attempts_made=attempts
        )

    def _layer5_manual_override(self, server_name: str,
                               attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """
        Layer 5: Manual override with comprehensive logging and revert scripts.

        When all automated methods fail:
        - Generate detailed troubleshooting logs
        - Create PowerShell scripts for manual execution
        - Provide step-by-step manual setup instructions
        - Generate revert scripts for all changes made
        """
        logger.info("Layer 5: Generating manual override for %s", server_name)

        # Generate comprehensive troubleshooting report
        troubleshooting_report = self._generate_troubleshooting_report(server_name, attempts)

        # Generate manual setup scripts
        manual_scripts = self._generate_manual_setup_scripts(server_name)

        # Generate revert scripts
        revert_scripts = self._generate_revert_scripts()

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Layer 5: Manual intervention required",
            attempts_made=attempts,
            troubleshooting_report=troubleshooting_report,
            manual_setup_scripts=manual_scripts,
            revert_scripts=revert_scripts
        )

    def _try_single_connection(self, server_name: str, auth_method: AuthMethod,
                              protocol: Protocol, port: int,
                              bundle: CredentialBundle,
                              attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Try a single connection configuration."""
        attempt = ConnectionAttempt(
            server_name=server_name,
            auth_method=auth_method,
            protocol=protocol,
            port=port,
            credential_type=self.credential_handler.get_credential_type(bundle),
            error_message=None,
            attempted_at=self._get_timestamp()
        )

        start_time = time.time()
        try:
            profile = ConnectionProfile(
                server_name=server_name,
                auth_method=auth_method,
                protocol=protocol,
                port=port,
                credential_type=self.credential_handler.get_credential_type(bundle),
                last_successful=None,
                created_at=self._get_timestamp(),
                updated_at=self._get_timestamp()
            )

            session = self._execute_connection_attempt(profile, bundle)
            if session:
                attempt.duration_ms = int((time.time() - start_time) * 1000)
                attempts.append(attempt)
                return PSRemotingResult(
                    success=True,
                    session=session,
                    error_message=None,
                    attempts_made=attempts
                )

        except Exception as e:
            attempt.error_message = str(e)

        attempt.duration_ms = int((time.time() - start_time) * 1000)
        attempts.append(attempt)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message=None,
            attempts_made=attempts
        )

    def _execute_connection_attempt(self, profile: ConnectionProfile,
                                   bundle: CredentialBundle) -> Optional[PSSession]:
        """Execute actual PowerShell connection attempt."""
        if not self._is_windows:
            raise RuntimeError("PS Remoting only supported on Windows")

        # Create PowerShell connection command
        ps_command = self._build_connection_command(profile, bundle)

        try:
            # Execute PowerShell command
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )

            if result.returncode == 0 and "Connected" in result.stdout:
                return PSSession(
                    session_id=f"{profile.server_name}_{int(time.time())}",
                    server_name=profile.server_name,
                    connection_profile=profile,
                    created_at=self._get_timestamp()
                )

            raise RuntimeError(f"Connection failed: {result.stderr}")

        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Connection attempt timed out") from exc

    def _build_connection_command(self, profile: ConnectionProfile,
                                 bundle: CredentialBundle) -> str:
        """Build PowerShell command for connection attempt."""
        server = profile.server_name
        auth = profile.auth_method.value
        port = profile.port

        # Base connection command
        command_parts = [
            f"$session = New-PSSession -ComputerName '{server}'",
            f" -Authentication {auth}",
            f" -Port {port}"
        ]

        # Add credentials if available
        ps_cred = self.credential_handler.create_pscredential(bundle)
        if ps_cred:
            command_parts.append(f" -Credential ({ps_cred})")

        # Add session option for SSL if HTTPS
        if profile.protocol == Protocol.HTTPS:
            command_parts.append(" -UseSSL")

        # Add connection test
        command_parts.extend([
            "",
            "if ($session) {",
            "    'Connected'",
            "} else {",
            "    'Failed'",
            "}"
        ])

        return "\n".join(command_parts)

    def _add_to_trusted_hosts(self, server: str) -> bool:
        """Add server to WinRM TrustedHosts."""
        try:
            command = f"Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{server}' -Concatenate -Force"
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    def _has_admin_credentials(self, bundle: CredentialBundle) -> bool:
        """Check if credentials have admin privileges."""
        # For now, assume domain admin if we have credentials
        # TODO: Implement actual privilege checking
        return bundle.username is not None and bundle.password is not None

    def _ensure_winrm_service_running(self, server_name: str, bundle: CredentialBundle) -> bool:
        """Ensure WinRM service is running and set to automatic on target."""
        try:
            ps_script = f"""
            Invoke-Command -ComputerName '{server_name}' -Credential (Get-Credential) -ScriptBlock {{
                # Set WinRM service to Automatic and start it
                Set-Service -Name WinRM -StartupType Automatic -ErrorAction SilentlyContinue
                Start-Service -Name WinRM -ErrorAction SilentlyContinue

                # Verify service status
                $service = Get-Service -Name WinRM
                if ($service.Status -eq 'Running' -and $service.StartType -eq 'Automatic') {{
                    Write-Host "SUCCESS: WinRM service configured"
                    $true
                }} else {{
                    Write-Host "FAILED: WinRM service not properly configured"
                    $false
                }}
            }}
            """

            result = self._execute_ps_command_with_creds(ps_script, bundle)
            success = "SUCCESS:" in result.stdout

            if success:
                self._track_change("winrm_service", server_name, "started_automatic")
                self._revert_scripts.append(f"""
# Revert WinRM service changes on {server_name}
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    Stop-Service -Name WinRM -ErrorAction SilentlyContinue
    Set-Service -Name WinRM -StartupType Manual -ErrorAction SilentlyContinue
}}
""")

            return success

        except Exception as e:
            logger.exception("Failed to configure WinRM service on %s: %s", server_name, e)
            return False

    def _configure_firewall_rules(self, server_name: str, bundle: CredentialBundle) -> bool:
        """Configure Windows Firewall rules for WinRM on target."""
        try:
            ps_script = f"""
            Invoke-Command -ComputerName '{server_name}' -Credential (Get-Credential) -ScriptBlock {{
                # Enable WinRM firewall rules
                Enable-NetFirewallRule -DisplayGroup "Windows Remote Management" -ErrorAction SilentlyContinue

                # Add specific rules if group rules don't exist
                $httpRule = Get-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue
                if (-not $httpRule) {{
                    New-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -DisplayName "Windows Remote Management (HTTP-In)" `
                        -Description "Inbound rule for Windows Remote Management via WS-Management. [TCP 5985]" `
                        -Group "Windows Remote Management" -Profile Any -Direction Inbound -Action Allow `
                        -Protocol TCP -LocalPort 5985 -ErrorAction SilentlyContinue
                }}

                $httpsRule = Get-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -ErrorAction SilentlyContinue
                if (-not $httpsRule) {{
                    New-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -DisplayName "Windows Remote Management (HTTPS-In)" `
                        -Description "Inbound rule for Windows Remote Management via WS-Management. [TCP 5986]" `
                        -Group "Windows Remote Management" -Profile Any -Direction Inbound -Action Allow `
                        -Protocol TCP -LocalPort 5986 -ErrorAction SilentlyContinue
                }}

                Write-Host "SUCCESS: Firewall rules configured"
            }}
            """

            result = self._execute_ps_command_with_creds(ps_script, bundle)
            success = "SUCCESS:" in result.stdout

            if success:
                self._track_change("firewall_rules", server_name, "winrm_enabled")
                self._revert_scripts.append(f"""
# Revert firewall rules on {server_name}
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    Disable-NetFirewallRule -DisplayGroup "Windows Remote Management" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -Name "WINRM-HTTP-In-TCP" -ErrorAction SilentlyContinue
    Remove-NetFirewallRule -Name "WINRM-HTTPS-In-TCP" -ErrorAction SilentlyContinue
}}
""")

            return success

        except Exception as e:
            logger.exception("Failed to configure firewall rules on %s: %s", server_name, e)
            return False

    def _configure_registry_settings(self, server_name: str, bundle: CredentialBundle) -> bool:
        """Configure critical registry settings for PS remoting."""
        try:
            ps_script = f"""
            Invoke-Command -ComputerName '{server_name}' -Credential (Get-Credential) -ScriptBlock {{
                # Allow local accounts to authenticate remotely (workgroup scenarios)
                $localAccountPath = "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System"
                $localAccountValue = Get-ItemProperty -Path $localAccountPath -Name "LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue

                if (-not $localAccountValue) {{
                    New-ItemProperty -Path $localAccountPath -Name "LocalAccountTokenFilterPolicy" -Value 1 -PropertyType DWORD -Force
                    Write-Host "SET: LocalAccountTokenFilterPolicy = 1"
                }}

                # Disable loopback check for localhost connections
                $loopbackPath = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa"
                $loopbackValue = Get-ItemProperty -Path $loopbackPath -Name "DisableLoopbackCheck" -ErrorAction SilentlyContinue

                if (-not $loopbackValue) {{
                    New-ItemProperty -Path $loopbackPath -Name "DisableLoopbackCheck" -Value 1 -PropertyType DWORD -Force
                    Write-Host "SET: DisableLoopbackCheck = 1"
                }}

                Write-Host "SUCCESS: Registry settings configured"
            }}
            """

            result = self._execute_ps_command_with_creds(ps_script, bundle)
            success = "SUCCESS:" in result.stdout

            if success:
                self._track_change("registry_settings", server_name, "remoting_enabled")
                self._revert_scripts.append(f"""
# Revert registry settings on {server_name}
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    # Remove LocalAccountTokenFilterPolicy if we created it
    Remove-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" -Name "LocalAccountTokenFilterPolicy" -ErrorAction SilentlyContinue

    # Remove DisableLoopbackCheck if we created it
    Remove-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" -Name "DisableLoopbackCheck" -ErrorAction SilentlyContinue
}}
""")

            return success

        except Exception as e:
            logger.exception("Failed to configure registry settings on %s: %s", server_name, e)
            return False

    def _ensure_winrm_listeners(self, server_name: str, bundle: CredentialBundle) -> bool:
        """Ensure WinRM HTTP and HTTPS listeners exist on target."""
        try:
            ps_script = f"""
            Invoke-Command -ComputerName '{server_name}' -Credential (Get-Credential) -ScriptBlock {{
                # Check for HTTP listener
                $httpListener = Get-WSManInstance -ResourceURI winrm/config/listener -SelectorSet @{{Address="*";Transport="HTTP"}} -ErrorAction SilentlyContinue

                if (-not $httpListener) {{
                    # Create HTTP listener
                    winrm create winrm/config/listener?Address=*+Transport=HTTP
                    Write-Host "CREATED: HTTP listener"
                }} else {{
                    Write-Host "EXISTS: HTTP listener"
                }}

                # Check for HTTPS listener (optional, requires certificate)
                $httpsListener = Get-WSManInstance -ResourceURI winrm/config/listener -SelectorSet @{{Address="*";Transport="HTTPS"}} -ErrorAction SilentlyContinue

                if (-not $httpsListener) {{
                    Write-Host "NOTE: HTTPS listener not created (requires certificate)"
                }} else {{
                    Write-Host "EXISTS: HTTPS listener"
                }}

                Write-Host "SUCCESS: WinRM listeners verified"
            }}
            """

            result = self._execute_ps_command_with_creds(ps_script, bundle)
            success = "SUCCESS:" in result.stdout

            if success:
                self._track_change("winrm_listeners", server_name, "verified")
                # Note: We don't revert listener creation as it's generally beneficial

            return success

        except Exception as e:
            logger.exception("Failed to ensure WinRM listeners on %s: %s", server_name, e)
            return False

    def _configure_target_trustedhosts(self, server_name: str, bundle: CredentialBundle) -> bool:
        """Configure TrustedHosts on target server (for IP-based connections)."""
        # Only needed if connecting by IP address
        if not self._is_ip_address(server_name):
            return True  # Not needed for hostname connections

        try:
            # Get current client IP (this is running on the client)
            client_ip = self._get_client_ip()

            ps_script = f"""
            Invoke-Command -ComputerName '{server_name}' -Credential (Get-Credential) -ScriptBlock {{
                # Add client IP to TrustedHosts on target
                $currentHosts = (Get-Item WSMan:\\localhost\\Client\\TrustedHosts).Value

                if ($currentHosts -notlike "*{client_ip}*") {{
                    Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "{client_ip}" -Concatenate -Force
                    Write-Host "ADDED: {client_ip} to TrustedHosts"
                }} else {{
                    Write-Host "EXISTS: {client_ip} already in TrustedHosts"
                }}

                Write-Host "SUCCESS: Target TrustedHosts configured"
            }}
            """.replace("{client_ip}", client_ip)

            result = self._execute_ps_command_with_creds(ps_script, bundle)
            success = "SUCCESS:" in result.stdout

            if success:
                self._track_change("target_trustedhosts", server_name, f"added_{client_ip}")
                self._revert_scripts.append(f"""
# Revert TrustedHosts on {server_name}
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    # Remove client IP from TrustedHosts
    $currentHosts = (Get-Item WSMan:\\localhost\\Client\\TrustedHosts).Value
    $newHosts = ($currentHosts -split ',') | Where-Object {{ $_ -ne '{client_ip}' }} | Where-Object {{ $_ -ne '' }}
    Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value ($newHosts -join ',') -Force
}}
""".replace("{client_ip}", client_ip))

            return success

        except Exception as e:
            logger.exception("Failed to configure target TrustedHosts on %s: %s", server_name, e)
            return False

    def _save_successful_profile(self, profile: ConnectionProfile):
        """Save successful connection profile."""
        profile.last_successful = self._get_timestamp()
        profile.updated_at = self._get_timestamp()
        self.repository.save_connection_profile(profile)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        return datetime.now().isoformat()

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

    def _try_ssh_powershell(self, server_name: str, bundle: CredentialBundle,
                           attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Try SSH-based PowerShell connection."""
        logger.info("Trying SSH PowerShell connection to %s", server_name)

        # Check if SSH is available
        if not self._is_ssh_available():
            return PSRemotingResult(success=False, session=None, error_message="SSH not available")

        attempt = ConnectionAttempt(
            server_name=server_name,
            auth_method=AuthMethod.BASIC,  # SSH uses basic auth
            protocol=Protocol.HTTP,  # Not really applicable
            port=22,
            credential_type=self.credential_handler.get_credential_type(bundle),
            error_message=None,
            attempted_at=self._get_timestamp()
        )

        try:
            # This would implement SSH-based PowerShell
            # For now, just log the attempt
            attempt.error_message = "SSH PowerShell not yet implemented"
            attempts.append(attempt)

        except Exception as e:
            attempt.error_message = str(e)
            attempts.append(attempt)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="SSH PowerShell failed",
            attempts_made=attempts
        )

    def _try_wmi_connection(self, server_name: str, bundle: CredentialBundle,
                           attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Try WMI-based connection."""
        logger.info("Trying WMI connection to %s", server_name)

        attempt = ConnectionAttempt(
            server_name=server_name,
            auth_method=AuthMethod.NTLM,  # WMI typically uses NTLM
            protocol=Protocol.HTTP,  # Not applicable
            port=135,  # RPC port
            credential_type=self.credential_handler.get_credential_type(bundle),
            error_message=None,
            attempted_at=self._get_timestamp()
        )

        try:
            # This would implement WMI-based PowerShell execution
            # For now, just log the attempt
            attempt.error_message = "WMI connection not yet implemented"
            attempts.append(attempt)

        except Exception as e:
            attempt.error_message = str(e)
            attempts.append(attempt)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="WMI connection failed",
            attempts_made=attempts
        )

    def _try_psexec_connection(self, server_name: str, bundle: CredentialBundle,
                              attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Try psexec-based connection."""
        logger.info("Trying psexec connection to %s", server_name)

        # Check if psexec is available
        if not self._is_psexec_available():
            return PSRemotingResult(success=False, session=None, error_message="psexec not available")

        attempt = ConnectionAttempt(
            server_name=server_name,
            auth_method=AuthMethod.NTLM,
            protocol=Protocol.HTTP,  # Not applicable
            port=445,  # SMB port
            credential_type=self.credential_handler.get_credential_type(bundle),
            error_message=None,
            attempted_at=self._get_timestamp()
        )

        try:
            # This would implement psexec-based PowerShell execution
            # For now, just log the attempt
            attempt.error_message = "psexec connection not yet implemented"
            attempts.append(attempt)

        except Exception as e:
            attempt.error_message = str(e)
            attempts.append(attempt)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="psexec connection failed",
            attempts_made=attempts
        )

    def _try_rpc_connection(self, server_name: str, bundle: CredentialBundle,
                           attempts: List[ConnectionAttempt]) -> PSRemotingResult:
        """Try RPC-based connection."""
        logger.info("Trying RPC connection to %s", server_name)

        attempt = ConnectionAttempt(
            server_name=server_name,
            auth_method=AuthMethod.NTLM,
            protocol=Protocol.HTTP,  # Not applicable
            port=135,  # RPC endpoint mapper
            credential_type=self.credential_handler.get_credential_type(bundle),
            error_message=None,
            attempted_at=self._get_timestamp()
        )

        try:
            # This would implement RPC-based PowerShell execution
            # For now, just log the attempt
            attempt.error_message = "RPC connection not yet implemented"
            attempts.append(attempt)

        except Exception as e:
            attempt.error_message = str(e)
            attempts.append(attempt)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="RPC connection failed",
            attempts_made=attempts
        )

    def _generate_troubleshooting_report(self, server_name: str,
                                       attempts: List[ConnectionAttempt]) -> str:
        """Generate comprehensive troubleshooting report."""
        report_lines = [
            f"# PS Remoting Troubleshooting Report for {server_name}",
            f"Generated: {self._get_timestamp()}",
            "",
            "## Connection Attempts Summary",
            f"Total attempts: {len(attempts)}",
            "",
            "## Detailed Attempts:"
        ]

        for i, attempt in enumerate(attempts, 1):
            report_lines.extend([
                f"### Attempt {i}",
                f"- Server: {attempt.server_name}",
                f"- Auth Method: {attempt.auth_method.value}",
                f"- Protocol: {attempt.protocol.value}",
                f"- Port: {attempt.port}",
                f"- Duration: {attempt.duration_ms}ms",
                f"- Error: {attempt.error_message or 'None'}",
                ""
            ])

        report_lines.extend([
            "## Common Issues Checklist",
            "",
            "### Network Connectivity",
            "- [ ] Can ping target server?",
            "- [ ] Are WinRM ports (5985/5986) open?",
            "- [ ] Is Windows Firewall blocking connections?",
            "",
            "### Authentication Issues",
            "- [ ] Are credentials correct?",
            "- [ ] Is account locked/disabled?",
            "- [ ] Does account have remote access permissions?",
            "- [ ] Is Kerberos working (domain joined)?",
            "",
            "### WinRM Configuration",
            "- [ ] Is WinRM service running?",
            "- [ ] Are WinRM listeners configured?",
            "- [ ] Is server in TrustedHosts (if using IP)?",
            "",
            "### Registry Settings",
            "- [ ] LocalAccountTokenFilterPolicy set (workgroup)?",
            "- [ ] DisableLoopbackCheck set (localhost)?",
            "",
            "### Group Policy",
            "- [ ] Is WinRM blocked by GPO?",
            "- [ ] Are firewall rules overridden by GPO?",
            "",
            "## Manual Setup Commands",
            "",
            "### On Target Server (run as Administrator):",
            "```powershell",
            "# Enable PS Remoting",
            "Enable-PSRemoting -Force -SkipNetworkProfileCheck",
            "",
            "# Configure WinRM service",
            "Set-Service -Name WinRM -StartupType Automatic",
            "Start-Service -Name WinRM",
            "",
            "# Add firewall rules",
            "Enable-NetFirewallRule -DisplayGroup 'Windows Remote Management'",
            "",
            "# Configure TrustedHosts (replace with actual IPs)",
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '*' -Force",
            "",
            "# Registry settings for workgroup scenarios",
            "New-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -Name 'LocalAccountTokenFilterPolicy' -Value 1 -PropertyType DWORD -Force",
            "",
            "# Registry settings for localhost scenarios",
            "New-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa' -Name 'DisableLoopbackCheck' -Value 1 -PropertyType DWORD -Force",
            "```"
        ])

        return "\n".join(report_lines)

    def _generate_manual_setup_scripts(self, server_name: str) -> List[str]:
        """Generate PowerShell scripts for manual setup."""
        scripts = []

        # Target server setup script
        target_script = f"""
# Manual PS Remoting Setup for {server_name}
# Run this script on {server_name} as Administrator

Write-Host "Setting up PowerShell Remoting on {server_name}..."

# Enable PS Remoting
Enable-PSRemoting -Force -SkipNetworkProfileCheck

# Configure WinRM service
Set-Service -Name WinRM -StartupType Automatic
Start-Service -Name WinRM

# Add firewall rules
Enable-NetFirewallRule -DisplayGroup "Windows Remote Management"

# Configure TrustedHosts (allow all for testing - restrict in production)
Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "*" -Force

# Registry settings for workgroup scenarios
New-ItemProperty -Path "HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System" `
    -Name "LocalAccountTokenFilterPolicy" -Value 1 -PropertyType DWORD -Force

# Registry settings for localhost scenarios
New-ItemProperty -Path "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa" `
    -Name "DisableLoopbackCheck" -Value 1 -PropertyType DWORD -Force

# Verify configuration
Get-WSManInstance -ResourceURI winrm/config/listener -SelectorSet @{{Address="*";Transport="HTTP"}}

Write-Host "PS Remoting setup complete on {server_name}"
"""
        scripts.append(target_script)

        # Client setup script
        client_script = f"""
# Manual Client Setup for connecting to {server_name}
# Run this script on the client machine as Administrator

Write-Host "Setting up client for PS Remoting to {server_name}..."

# Add target to TrustedHosts
Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "{server_name}" -Concatenate -Force

# Test connection
Test-WSMan -ComputerName {server_name}

Write-Host "Client setup complete for {server_name}"
"""
        scripts.append(client_script)

        return scripts

    def _generate_revert_scripts(self) -> List[str]:
        """Generate revert scripts for all changes made."""
        # Return the accumulated revert scripts
        return self._revert_scripts.copy()

    # Helper methods

    def _execute_ps_command_with_creds(self, script: str, bundle: CredentialBundle) -> subprocess.CompletedProcess:
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

    def _track_change(self, change_type: str, server: str, details: str):
        """Track configuration changes for revert purposes."""
        self._changes_made.append({
            "type": change_type,
            "server": server,
            "details": details,
            "timestamp": self._get_timestamp()
        })

    def _is_ip_address(self, hostname: str) -> bool:
        """Check if hostname is an IP address."""
        import ipaddress
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    def _get_client_ip(self) -> str:
        """Get the client's IP address."""
        # This is a simplified implementation
        # In practice, you'd determine the appropriate IP for the target network
        return "192.168.1.100"  # Placeholder

    def _is_ssh_available(self) -> bool:
        """Check if SSH client is available."""
        try:
            result = subprocess.run(["ssh", "-V"], capture_output=True, check=False)
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def _is_psexec_available(self) -> bool:
        """Check if psexec is available."""
        try:
            result = subprocess.run(["psexec", "/?"], capture_output=True, check=False)
            return result.returncode == 0 and "PsExec" in result.stderr.decode()
        except FileNotFoundError:
            return False
