"""
Domain enums for configuration system.

This module defines all enumeration types used in the configuration domain.
"""

from enum import Enum


class AuthType(Enum):
    """Authentication types for SQL Server connections."""

    WINDOWS = "windows"
    INTEGRATED = "integrated"  # alias for WINDOWS (back-compat with configs)
    SQL = "sql"


class OSType(Enum):
    """Operating system types for target servers."""
    WINDOWS = "windows"
    LINUX = "linux"
    UNKNOWN = "unknown"


class ConnectionMethod(Enum):
    """Methods for connecting to target servers."""
    POWERSHELL_REMOTING = "powershell_remoting"
    SSH = "ssh"
    WINRM = "winrm"
    DIRECT = "direct"
