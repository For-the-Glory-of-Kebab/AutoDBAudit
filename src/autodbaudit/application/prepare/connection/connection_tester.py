"""
Connection Testing Service - Ultra-granular component for connection validation.

This module provides specialized connection testing capabilities using
multiple protocols and intelligent retry logic.
"""

import logging
import socket
import subprocess
import time
from typing import List

from autodbaudit.domain.config import ConnectionMethod

logger = logging.getLogger(__name__)


class ConnectionTestingService:
    """
    Specialized service for testing server connections.

    Tests multiple connection methods with intelligent retry and timeout logic.
    """

    def __init__(self, max_retries: int = 3, base_timeout: float = 5.0) -> None:
        """
        Initialize the connection testing service.

        Args:
            max_retries: Maximum number of retry attempts
            base_timeout: Base timeout for connection attempts
        """
        self.max_retries = max_retries
        self.base_timeout = base_timeout
        self._test_cache: dict[tuple[str, ConnectionMethod], bool] = {}

    def test_connection(
        self,
        server: str,
        method: ConnectionMethod,
        use_cache: bool = True
    ) -> bool:
        """
        Test connection to server using specified method.

        Args:
            server: Target server
            method: Connection method to test
            use_cache: Whether to use cached results

        Returns:
            True if connection successful
        """
        cache_key = (server, method)
        if use_cache and cache_key in self._test_cache:
            return self._test_cache[cache_key]

        logger.debug("Testing %s connection to %s", method.value, server)

        # Test with retry logic
        for attempt in range(self.max_retries):
            try:
                timeout = self.base_timeout * (2 ** attempt)  # Exponential backoff
                result = self._test_method(server, method, timeout)

                if result:
                    logger.info("Connection test successful: %s -> %s",
                              method.value, server)
                    if use_cache:
                        self._test_cache[cache_key] = True
                    return True

            except Exception as e:
                logger.debug("Connection test attempt %d failed for %s:%s: %s",
                           attempt + 1, server, method.value, e)

            if attempt < self.max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))  # Exponential backoff delay

        logger.warning("Connection test failed after %d attempts: %s -> %s",
                      self.max_retries, method.value, server)
        if use_cache:
            self._test_cache[cache_key] = False
        return False

    def get_available_methods(self, server: str) -> List[ConnectionMethod]:
        """
        Get all available connection methods for a server.

        Args:
            server: Target server

        Returns:
            List of available connection methods
        """
        available_methods = []

        # Test each method
        for method in ConnectionMethod:
            if self.test_connection(server, method, use_cache=True):
                available_methods.append(method)

        logger.info("Available connection methods for %s: %s",
                   server, [m.value for m in available_methods])
        return available_methods

    def _test_method(
        self,
        server: str,
        method: ConnectionMethod,
        timeout: float
    ) -> bool:
        """
        Test a specific connection method.

        Args:
            server: Target server
            method: Connection method to test
            timeout: Timeout for the test

        Returns:
            True if method works
        """
        match method:
            case ConnectionMethod.POWERSHELL_REMOTING:
                return self._test_powershell(server, timeout)
            case ConnectionMethod.SSH:
                return self._test_ssh(server, timeout)
            case ConnectionMethod.WINRM:
                return self._test_winrm(server, timeout)
            case ConnectionMethod.DIRECT:
                return self._test_direct(server, timeout)
            case _:
                logger.warning("Unknown connection method: %s", method)
                return False

    def _test_powershell(self, server: str, timeout: float) -> bool:
        """Test PowerShell remoting connection."""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 f"Test-Connection -ComputerName {server} -Count 1 -Quiet"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode == 0 and "True" in result.stdout
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False

    def _test_ssh(self, server: str, timeout: float) -> bool:
        """Test SSH connection."""
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "-o", "BatchMode=yes",
                 "-o", "StrictHostKeyChecking=no", server, "echo 'test'"],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            return False

    def _test_winrm(self, _server: str, _timeout: float) -> bool:
        """Test WinRM connection."""
        # Placeholder - would need pywinrm or similar
        logger.debug("WinRM testing not yet implemented")
        return False

    def _test_direct(self, server: str, timeout: float) -> bool:
        """Test direct TCP connection."""
        try:
            # Test common SQL Server port
            with socket.create_connection((server, 1433), timeout=timeout):
                return True
        except (socket.timeout, socket.error):
            return False

    def clear_cache(self) -> None:
        """Clear the connection test cache."""
        self._test_cache.clear()
        logger.info("Connection test cache cleared")
