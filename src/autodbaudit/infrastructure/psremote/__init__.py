"""
PSRemote Infrastructure Package.

Ultra-resilient PowerShell remoting using pywinrm.
Tries every possible authentication and transport combination.
"""

from autodbaudit.infrastructure.psremote.client import (
    PSRemoteClient,
    PSRemoteResult,
    ConnectionConfig,
)
from autodbaudit.infrastructure.psremote.executor import (
    ScriptExecutor,
    ExecutionResult,
)

__all__ = [
    "PSRemoteClient",
    "PSRemoteResult",
    "ConnectionConfig",
    "ScriptExecutor",
    "ExecutionResult",
]
