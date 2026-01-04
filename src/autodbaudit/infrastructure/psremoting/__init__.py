"""
PowerShell Remoting Infrastructure

Core infrastructure for establishing and managing PowerShell remoting connections
to target SQL Server machines. Provides resilient connection establishment with
multiple fallback strategies and state persistence.
"""

from .models import (
    AuthMethod,
    Protocol,
    CredentialType,
    ConnectionState,
    ConnectionProfile,
    ConnectionAttempt,
    PSSession,
    CommandResult,
    ElevationStatus,
    CredentialBundle,
    PSRemotingResult,
    ServerState,
    ConnectionMethod,
)
from .elevation import ShellElevationService
from .credentials import CredentialHandler
from .repository import PSRemotingRepository
from .connection_manager import PSRemotingConnectionManager
from .facade import PSRemotingFacade

__all__ = [
    # Models
    "AuthMethod",
    "Protocol",
    "CredentialType",
    "ConnectionState",
    "ConnectionProfile",
    "ConnectionAttempt",
    "PSSession",
    "CommandResult",
    "ElevationStatus",
    "CredentialBundle",
    "PSRemotingResult",
    "ServerState",
    "ConnectionMethod",

    # Services
    "ShellElevationService",
    "CredentialHandler",
    "PSRemotingRepository",
    "PSRemotingConnectionManager",
    "PSRemotingFacade",
]
