"""
Connection Method Selection Service - Ultra-granular component for method selection.

This module provides intelligent connection method selection based on
OS type, availability, and performance characteristics.
"""

import logging
from typing import List, Optional

from autodbaudit.domain.config import ConnectionMethod, OSType

logger = logging.getLogger(__name__)


class ConnectionMethodSelector:
    """
    Specialized service for selecting optimal connection methods.

    Uses intelligent selection logic based on OS, availability, and preferences.
    """

    def __init__(self) -> None:
        """Initialize the connection method selector."""
        # Define method preferences by OS type
        self._os_preferences: dict[OSType, List[ConnectionMethod]] = {
            OSType.WINDOWS: [
                ConnectionMethod.POWERSHELL_REMOTING,
                ConnectionMethod.WINRM,
                ConnectionMethod.DIRECT,
                ConnectionMethod.SSH,
            ],
            OSType.LINUX: [
                ConnectionMethod.SSH,
                ConnectionMethod.DIRECT,
                ConnectionMethod.POWERSHELL_REMOTING,
                ConnectionMethod.WINRM,
            ],
            OSType.UNKNOWN: [
                ConnectionMethod.DIRECT,
                ConnectionMethod.SSH,
                ConnectionMethod.POWERSHELL_REMOTING,
                ConnectionMethod.WINRM,
            ],
        }

    def select_preferred_method(
        self,
        available_methods: List[ConnectionMethod],
        os_type: OSType
    ) -> Optional[ConnectionMethod]:
        """
        Select the preferred connection method.

        Args:
            available_methods: List of available connection methods
            os_type: Detected operating system type

        Returns:
            Preferred connection method or None if none available
        """
        if not available_methods:
            logger.warning("No connection methods available")
            return None

        # Get preferences for this OS type
        preferences = self._os_preferences.get(os_type, self._os_preferences[OSType.UNKNOWN])

        # Find the highest preference method that's available
        for preferred_method in preferences:
            if preferred_method in available_methods:
                logger.info("Selected connection method %s for OS %s",
                          preferred_method.value, os_type.value)
                return preferred_method

        # Fallback to first available method
        fallback_method = available_methods[0]
        logger.warning("No preferred method available, using fallback: %s",
                      fallback_method.value)
        return fallback_method

    def get_method_priority(self, method: ConnectionMethod, os_type: OSType) -> int:
        """
        Get the priority score for a connection method.

        Args:
            method: Connection method to evaluate
            os_type: Target operating system

        Returns:
            Priority score (lower is better)
        """
        preferences = self._os_preferences.get(os_type, self._os_preferences[OSType.UNKNOWN])

        try:
            return preferences.index(method)
        except ValueError:
            return len(preferences)  # Lowest priority for unknown methods

    def rank_methods(
        self,
        methods: List[ConnectionMethod],
        os_type: OSType
    ) -> List[ConnectionMethod]:
        """
        Rank connection methods by preference for the given OS.

        Args:
            methods: List of methods to rank
            os_type: Target operating system

        Returns:
            Methods sorted by preference (best first)
        """
        return sorted(methods, key=lambda m: self.get_method_priority(m, os_type))

    def is_method_suitable(
        self,
        method: ConnectionMethod,
        os_type: OSType
    ) -> bool:
        """
        Check if a connection method is suitable for the OS type.

        Args:
            method: Connection method to check
            os_type: Target operating system

        Returns:
            True if method is suitable
        """
        # All methods are potentially suitable, but some are preferred
        return True

    def get_fallback_methods(
        self,
        failed_method: ConnectionMethod,
        available_methods: List[ConnectionMethod],
        os_type: OSType
    ) -> List[ConnectionMethod]:
        """
        Get fallback methods when a preferred method fails.

        Args:
            failed_method: Method that failed
            available_methods: All available methods
            os_type: Target operating system

        Returns:
            List of fallback methods in preference order
        """
        remaining_methods = [m for m in available_methods if m != failed_method]
        return self.rank_methods(remaining_methods, os_type)
    
