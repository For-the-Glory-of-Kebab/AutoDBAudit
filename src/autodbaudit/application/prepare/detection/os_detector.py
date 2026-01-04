"""
OS Detection Service - Ultra-granular component for operating system detection.

This module provides specialized OS detection capabilities using multiple
connection methods and fallback strategies.
"""

import logging
import socket
import subprocess
from typing import Optional

from autodbaudit.domain.config import OSType

logger = logging.getLogger(__name__)


class OSDetectionService:
    """
    Specialized service for detecting server operating systems.

    Uses multiple detection strategies with intelligent fallback logic.
    """

    def __init__(self) -> None:
        """Initialize the OS detection service."""
        self._detection_cache: dict[str, OSType] = {}

    def detect_os(self, server: str, use_cache: bool = True) -> OSType:
        """
        Detect the operating system of a target server.

        Args:
            server: Server hostname or IP address
            use_cache: Whether to use cached results

        Returns:
            Detected operating system type
        """
        if use_cache and server in self._detection_cache:
            return self._detection_cache[server]

        logger.debug("Detecting OS for server: %s", server)

        # Try multiple detection methods in order of preference
        detection_methods = [
            self._detect_via_powershell,
            self._detect_via_ssh,
            self._detect_via_connectivity,
        ]

        for method in detection_methods:
            try:
                os_type = method(server)
                if os_type != OSType.UNKNOWN:
                    logger.info("Detected OS %s for server %s using %s",
                              os_type.value, server, method.__name__)
                    if use_cache:
                        self._detection_cache[server] = os_type
                    return os_type
            except Exception as e:
                logger.debug("OS detection method %s failed for %s: %s",
                           method.__name__, server, e)

        # Default to unknown if all methods fail
        logger.warning("Could not determine OS for server: %s", server)
        default_os = OSType.UNKNOWN
        if use_cache:
            self._detection_cache[server] = default_os
        return default_os

    def _detect_via_powershell(self, server: str) -> OSType:
        """
        Detect OS using PowerShell remoting.

        Args:
            server: Target server

        Returns:
            Detected OS type
        """
        try:
            result = self._run_powershell_command(
                server,
                "$PSVersionTable.Platform",
                timeout=10
            )
            if result:
                result_lower = result.lower()
                if "unix" in result_lower or "linux" in result_lower:
                    return OSType.LINUX
                if "win" in result_lower:
                    return OSType.WINDOWS
        except Exception:
            pass
        return OSType.UNKNOWN

    def _detect_via_ssh(self, server: str) -> OSType:
        """
        Detect OS using SSH connection.

        Args:
            server: Target server

        Returns:
            Detected OS type
        """
        try:
            result = self._run_ssh_command(
                server,
                "uname -s",
                timeout=10
            )
            if result and "linux" in result.lower():
                return OSType.LINUX
        except Exception:
            pass
        return OSType.UNKNOWN

    def _detect_via_connectivity(self, server: str) -> OSType:
        """
        Detect OS using basic connectivity patterns.

        Args:
            server: Target server

        Returns:
            Detected OS type (assumes Windows if reachable)
        """
        # Test common Windows ports
        windows_ports = [445, 3389]  # SMB, RDP
        for port in windows_ports:
            try:
                with socket.create_connection((server, port), timeout=3):
                    return OSType.WINDOWS
            except (socket.timeout, socket.error):
                continue

        # Test Linux SSH port
        try:
            with socket.create_connection((server, 22), timeout=3):
                return OSType.LINUX
        except (socket.timeout, socket.error):
            pass

        return OSType.UNKNOWN

    def _run_powershell_command(
        self,
        server: str,
        command: str,
        timeout: int = 30
    ) -> Optional[str]:
        """
        Execute PowerShell command on remote server.

        Args:
            server: Target server
            command: PowerShell command to execute
            timeout: Command timeout in seconds

        Returns:
            Command output or None if failed
        """
        try:
            ps_command = (
                f"Invoke-Command -ComputerName {server} "
                f"-ScriptBlock {{ {command} }} -ErrorAction Stop"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_command],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return None

    def _run_ssh_command(
        self,
        server: str,
        command: str,
        timeout: int = 30
    ) -> Optional[str]:
        """
        Execute SSH command on remote server.

        Args:
            server: Target server
            command: SSH command to execute
            timeout: Command timeout in seconds

        Returns:
            Command output or None if failed
        """
        try:
            result = subprocess.run(
                ["ssh", server, command],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return None

    def clear_cache(self) -> None:
        """Clear the OS detection cache."""
        self._detection_cache.clear()
        logger.info("OS detection cache cleared")
