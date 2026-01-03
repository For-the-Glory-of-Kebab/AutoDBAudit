"""
Direct connection attempt runner for PowerShell remoting.

Encapsulates Layer 1 direct connection attempts so the main connection manager
can stay focused on orchestration. All timing, attempt logging, and profile
construction live here.
"""

import time
import subprocess
import logging
from dataclasses import dataclass
from typing import List, Optional, Callable, Union

from .models import (
    AuthMethod,
    Protocol,
    ConnectionMethod,
    ConnectionProfile,
    ConnectionAttempt,
    PSSession,
    PSRemotingResult,
    CredentialBundle,
)
from .credentials import CredentialHandler

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ConnectionPlan:
    """Connection attempt configuration container."""

    server_name: str
    auth_method: Union[AuthMethod, str]
    protocol: Union[Protocol, str]
    port: int


class DirectAttemptRunner:
    """Executes direct (Layer 1) PowerShell remoting attempts."""

    def __init__(
        self,
        credential_handler: CredentialHandler,
        timestamp_provider: Callable[[], str],
        is_windows: bool,
    ):
        self.credential_handler = credential_handler
        self._timestamp = timestamp_provider
        self._is_windows = is_windows

    def layer1_direct_attempts(
        self,
        server_name: str,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
    ) -> PSRemotingResult:
        """Try all direct connection permutations."""
        base_auth_methods = [
            AuthMethod.DEFAULT,
            AuthMethod.KERBEROS,
            AuthMethod.NTLM,
            AuthMethod.NEGOTIATE,
            AuthMethod.BASIC,
            AuthMethod.CREDSsp,
        ]
        protocols = [Protocol.HTTP, Protocol.HTTPS]
        ports = [5985, 5986]  # HTTP, HTTPS
        credential_variants = self._credential_variants(bundle)

        for auth_method in base_auth_methods:
            for protocol in protocols:
                for port in ports:
                    for username, password in credential_variants:
                        plan = ConnectionPlan(
                            server_name=server_name,
                            auth_method=auth_method,
                            protocol=protocol,
                            port=port,
                        )
                        result = self.try_single_connection(
                            plan, bundle, attempts, profile_id, username, password
                        )
                        if result.is_success():
                            return result

        return PSRemotingResult(
            success=False,
            session=None,
            error_message="Layer 1: All direct attempts failed",
            attempts_made=attempts,
            duration_ms=0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=None,
        )

    def try_single_connection(
        self,
        plan: ConnectionPlan,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> PSRemotingResult:
        """Try a single connection configuration."""
        attempt = ConnectionAttempt(
            profile_id=profile_id,
            server_name=plan.server_name,
            auth_method=self._enum_to_value(plan.auth_method),
            protocol=self._enum_to_value(plan.protocol),
            port=plan.port,
            credential_type=self._enum_to_value(self.credential_handler.get_credential_type(bundle)),
            error_message=None,
            attempted_at=self._timestamp(),
            attempt_timestamp=self._timestamp(),
            layer="direct",
            connection_method=ConnectionMethod.POWERSHELL_REMOTING,
            created_at=self._timestamp(),
            duration_ms=0,
            config_changes=None,
            rollback_actions=None,
            manual_script_path=None,
        )

        start_time = time.time()
        try:
            profile = self._build_connection_profile(plan, bundle)
            session = self._execute_connection_attempt(
                profile,
                bundle,
                username_override=username_override,
                password_override=password_override,
            )
            if session:
                attempt.duration_ms = int((time.time() - start_time) * 1000)
                attempt.success = True
                attempts.append(attempt)
                return PSRemotingResult(
                    success=True,
                    session=session,
                    error_message=None,
                    attempts_made=attempts,
                    duration_ms=attempt.duration_ms or 0,
                    troubleshooting_report=None,
                    manual_setup_scripts=None,
                    revert_scripts=None,
                )

        except Exception as exc:  # pylint: disable=broad-except
            attempt.error_message = str(exc)
            logger.debug("Direct attempt failed for %s: %s", plan.server_name, exc)

        attempt.duration_ms = int((time.time() - start_time) * 1000)
        attempts.append(attempt)

        return PSRemotingResult(
            success=False,
            session=None,
            error_message=attempt.error_message,
            attempts_made=attempts,
            duration_ms=attempt.duration_ms or 0,
            troubleshooting_report=None,
            manual_setup_scripts=None,
            revert_scripts=None,
        )

    def _build_connection_profile(
        self, plan: ConnectionPlan, bundle: CredentialBundle
    ) -> ConnectionProfile:
        """Construct a connection profile from plan and credentials."""
        auth_value = self._enum_to_value(plan.auth_method)
        protocol_value = self._enum_to_value(plan.protocol)
        credential_type = self._enum_to_value(self.credential_handler.get_credential_type(bundle))
        return ConnectionProfile(
            id=None,
            server_name=plan.server_name,
            connection_method=ConnectionMethod.POWERSHELL_REMOTING,
            auth_method=auth_value,
            protocol=protocol_value,
            port=plan.port,
            credential_type=credential_type,
            successful=False,
            last_successful_attempt=None,
            last_attempt=self._timestamp(),
            attempt_count=0,
            sql_targets=[],
            baseline_state=None,
            current_state=None,
            created_at=self._timestamp(),
            updated_at=self._timestamp(),
        )

    def connect_with_profile(
        self, profile: ConnectionProfile, bundle: CredentialBundle
    ) -> Optional[PSSession]:
        """
        Execute a connection attempt using an existing profile.

        Exposed for callers that persist successful profiles and want to reuse
        them without rebuilding the command logic here.
        """
        return self._execute_connection_attempt(profile, bundle)

    def _execute_connection_attempt(
        self,
        profile: ConnectionProfile,
        bundle: CredentialBundle,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> Optional[PSSession]:
        """Execute actual PowerShell connection attempt."""
        if not self._is_windows:
            raise RuntimeError("PS Remoting only supported on Windows")

        ps_command = self._build_connection_command(
            profile, bundle, username_override, password_override
        )

        result = subprocess.run(
            ["powershell", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        if result.returncode == 0 and "Connected" in result.stdout:
            return PSSession(
                session_id=f"{profile.server_name}_{int(time.time())}",
                server_name=profile.server_name,
                connection_profile=profile,
                created_at=self._timestamp(),
            )

        raise RuntimeError(f"Connection failed: {result.stderr}")

    def _build_connection_command(
        self,
        profile: ConnectionProfile,
        bundle: CredentialBundle,
        username_override: str | None = None,
        password_override: str | None = None,
    ) -> str:
        """Build PowerShell command for connection attempt."""
        server = profile.server_name
        auth = profile.auth_method or "Default"
        port = profile.port or 5985

        command_parts = [
            f"$session = New-PSSession -ComputerName '{server}'",
            f" -Authentication {auth}",
            f" -Port {port}",
        ]

        ps_cred = None
        if username_override and password_override:
            ps_cred = self.credential_handler.create_pscredential_from_parts(
                username_override, password_override
            )
        else:
            ps_cred = self.credential_handler.create_pscredential(bundle)
        if ps_cred:
            command_parts.append(f" -Credential ({ps_cred})")

        if (profile.protocol or "").lower() == Protocol.HTTPS.value:
            command_parts.append(" -UseSSL")
            command_parts.append(
                " -SessionOption (New-PSSessionOption -SkipCACheck -SkipCNCheck)"
            )

        # Allow unencrypted for Basic/NTLM in constrained environments
        if str(profile.auth_method).lower() in {AuthMethod.BASIC.value.lower(), AuthMethod.NTLM.value.lower()}:
            command_parts.append(" -AllowRedirection")
            command_parts.append(" -Authentication " + auth)
            command_parts.append(
                " -SessionOption (New-PSSessionOption -NoEncryption -SkipCACheck -SkipCNCheck)"
            )

        command_parts.extend(
            [
                "",
                "if ($session) {",
                "    'Connected'",
                "} else {",
                "    'Failed'",
                "}",
            ]
        )

        return "\n".join(command_parts)

    @staticmethod
    def _enum_to_value(value):
        """Return enum value or passthrough."""
        return value.value if hasattr(value, "value") else value

    def _credential_variants(self, bundle: CredentialBundle) -> list[tuple[str | None, str | None]]:
        """
        Build username/password permutations to exhaust domain/workgroup formats.

        Returns list of (username, password); None entries mean use default bundle creds.
        """
        variants: list[tuple[str | None, str | None]] = []
        win = bundle.windows_explicit or {}
        username = win.get("username")
        password = win.get("password")

        if username and password:
            variants.append((username, password))
            if "\\" in username:
                user_only = username.split("\\", 1)[1]
                variants.append((user_only, password))
            if "@" in username:
                variants.append((username.split("@")[0], password))
        variants.append((None, None))
        return variants
