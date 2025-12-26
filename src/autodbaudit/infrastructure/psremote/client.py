"""
PSRemote Client - Ultra-Resilient pywinrm Wrapper.

Tries every possible combination of transport and authentication
to establish a connection. Logs all attempts for debugging.

Transport Priority:
1. HTTPS (5986) with certificate validation
2. HTTPS (5986) without certificate validation
3. HTTP (5985)

Auth Priority:
1. Negotiate (auto-selects Kerberos or NTLM)
2. Kerberos
3. NTLM
4. Basic (only over HTTPS)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import winrm  # pywinrm

logger = logging.getLogger(__name__)


class Transport(Enum):
    """WinRM transport protocols."""

    HTTPS = "https"
    HTTP = "http"


class AuthMethod(Enum):
    """WinRM authentication methods."""

    NEGOTIATE = "negotiate"
    KERBEROS = "kerberos"
    NTLM = "ntlm"
    BASIC = "basic"


@dataclass
class ConnectionConfig:
    """Configuration for PSRemote connection."""

    hostname: str
    username: str | None = None
    password: str | None = None
    port_http: int = 5985
    port_https: int = 5986
    timeout_seconds: int = 30
    operation_timeout_sec: int = 120

    # Retry settings
    max_retries_per_combo: int = 2

    # SSL settings
    verify_ssl: bool = True
    ca_trust_path: str | None = None


@dataclass
class PSRemoteResult:
    """Result from PSRemote operation."""

    success: bool
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
    transport_used: str = ""
    auth_used: str = ""
    error: str = ""
    attempts: list[dict[str, Any]] = field(default_factory=list)


class PSRemoteClient:
    """
    Ultra-resilient PSRemote client using pywinrm.

    Tries every transport+auth combination until one works.
    Caches successful combination for future calls.
    """

    # Class-level cache of successful connections
    _connection_cache: dict[str, tuple[Transport, AuthMethod, bool]] = {}

    def __init__(self, config: ConnectionConfig) -> None:
        """Initialize with connection config."""
        self.config = config
        self._session: winrm.Session | None = None
        self._working_transport: Transport | None = None
        self._working_auth: AuthMethod | None = None
        self._working_verify_ssl: bool = True

    def connect(self) -> bool:
        """
        Establish connection trying all combinations.

        Returns True if connection established, False otherwise.
        """
        cache_key = f"{self.config.hostname}:{self.config.username}"

        # Check cache first
        if cache_key in self._connection_cache:
            transport, auth, verify_ssl = self._connection_cache[cache_key]
            logger.info("Using cached connection: %s + %s", transport.value, auth.value)
            if self._try_connect(transport, auth, verify_ssl):
                return True
            # Cache invalid, continue with full scan
            del self._connection_cache[cache_key]

        # Try all combinations
        attempts = []

        # HTTPS with SSL verification
        for auth in [AuthMethod.NEGOTIATE, AuthMethod.KERBEROS, AuthMethod.NTLM]:
            if self._try_connect(Transport.HTTPS, auth, verify_ssl=True):
                self._connection_cache[cache_key] = (Transport.HTTPS, auth, True)
                return True
            attempts.append({"transport": "https", "auth": auth.value, "ssl": True})

        # HTTPS without SSL verification
        for auth in [
            AuthMethod.NEGOTIATE,
            AuthMethod.KERBEROS,
            AuthMethod.NTLM,
            AuthMethod.BASIC,
        ]:
            if self._try_connect(Transport.HTTPS, auth, verify_ssl=False):
                self._connection_cache[cache_key] = (Transport.HTTPS, auth, False)
                logger.warning(
                    "Connected with SSL verification DISABLED - not recommended for production"
                )
                return True
            attempts.append({"transport": "https", "auth": auth.value, "ssl": False})

        # HTTP (only negotiate/kerberos/ntlm, never basic)
        for auth in [AuthMethod.NEGOTIATE, AuthMethod.KERBEROS, AuthMethod.NTLM]:
            if self._try_connect(Transport.HTTP, auth, verify_ssl=False):
                self._connection_cache[cache_key] = (Transport.HTTP, auth, False)
                logger.warning(
                    "Connected over HTTP - credentials transmitted in clear!"
                )
                return True
            attempts.append({"transport": "http", "auth": auth.value, "ssl": False})

        logger.error("All connection attempts failed for %s", self.config.hostname)
        return False

    def _try_connect(
        self, transport: Transport, auth: AuthMethod, verify_ssl: bool
    ) -> bool:
        """Try a single transport+auth combination."""
        port = (
            self.config.port_https
            if transport == Transport.HTTPS
            else self.config.port_http
        )
        endpoint = f"{transport.value}://{self.config.hostname}:{port}/wsman"

        logger.debug(
            "Trying: %s with %s (SSL verify: %s)", endpoint, auth.value, verify_ssl
        )

        for attempt in range(self.config.max_retries_per_combo):
            try:
                session = winrm.Session(
                    target=endpoint,
                    auth=(self.config.username, self.config.password),
                    transport=auth.value,
                    server_cert_validation="validate" if verify_ssl else "ignore",
                    operation_timeout_sec=self.config.operation_timeout_sec,
                    read_timeout_sec=self.config.timeout_seconds + 10,
                )

                # Test connection with simple command
                result = session.run_cmd("echo", ["OK"])

                if result.status_code == 0 and b"OK" in result.std_out:
                    logger.info("✓ Connected: %s + %s", transport.value, auth.value)
                    self._session = session
                    self._working_transport = transport
                    self._working_auth = auth
                    self._working_verify_ssl = verify_ssl
                    return True

            except Exception as e:
                logger.debug(
                    "Attempt %d failed: %s - %s",
                    attempt + 1,
                    type(e).__name__,
                    str(e)[:100],
                )

        return False

    def run_ps(self, script: str) -> PSRemoteResult:
        """
        Execute PowerShell script on remote host.

        Args:
            script: PowerShell script content

        Returns:
            PSRemoteResult with output and status
        """
        if not self._session:
            if not self.connect():
                return PSRemoteResult(
                    success=False,
                    error="Failed to establish connection",
                )

        try:
            result = self._session.run_ps(script)

            return PSRemoteResult(
                success=result.status_code == 0,
                stdout=result.std_out.decode("utf-8", errors="replace"),
                stderr=result.std_err.decode("utf-8", errors="replace"),
                return_code=result.status_code,
                transport_used=(
                    self._working_transport.value if self._working_transport else ""
                ),
                auth_used=self._working_auth.value if self._working_auth else "",
            )

        except Exception as e:
            logger.exception("PowerShell execution failed")
            return PSRemoteResult(
                success=False,
                error=str(e),
                transport_used=(
                    self._working_transport.value if self._working_transport else ""
                ),
                auth_used=self._working_auth.value if self._working_auth else "",
            )

    def run_cmd(self, command: str, args: list[str] | None = None) -> PSRemoteResult:
        """
        Execute CMD command on remote host.

        Args:
            command: Command to run
            args: Command arguments

        Returns:
            PSRemoteResult with output and status
        """
        if not self._session:
            if not self.connect():
                return PSRemoteResult(
                    success=False,
                    error="Failed to establish connection",
                )

        try:
            result = self._session.run_cmd(command, args or [])

            return PSRemoteResult(
                success=result.status_code == 0,
                stdout=result.std_out.decode("utf-8", errors="replace"),
                stderr=result.std_err.decode("utf-8", errors="replace"),
                return_code=result.status_code,
                transport_used=(
                    self._working_transport.value if self._working_transport else ""
                ),
                auth_used=self._working_auth.value if self._working_auth else "",
            )

        except Exception as e:
            logger.exception("Command execution failed")
            return PSRemoteResult(
                success=False,
                error=str(e),
            )

    def close(self) -> None:
        """Close the session."""
        self._session = None
