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
    ElevationStatus,
    CredentialBundle,
    PSRemotingResult
)
from .elevation import ShellElevationService
from .credentials import CredentialHandler
from .repository import PSRemotingRepository
from .connection_manager import PSRemotingConnectionManager

# Executor components (formerly psremote)
from .executor.connection_client import PSRemoteClient, ConnectionConfig, PSRemoteResult
from .executor.script_executor import ScriptExecutor, ExecutionResult
from .executor.os_data_invoker import PsRemoteOsDataInvoker

__all__ = [
    # Models
    "AuthMethod",
    "Protocol",
    "CredentialType",
    "ConnectionState",
    "ConnectionProfile",
    "ConnectionAttempt",
    "PSSession",
    "ElevationStatus",
    "CredentialBundle",
    "PSRemotingResult",

    # Services
    "ShellElevationService",
    "CredentialHandler",
    "PSRemotingRepository",
    "PSRemotingConnectionManager",

    # Executor components (formerly psremote)
    "PSRemoteClient",
    "ConnectionConfig",
    "PSRemoteResult",
    "ScriptExecutor",
    "ExecutionResult",
    "PsRemoteOsDataInvoker"
]
