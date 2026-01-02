"""
Prepare Server Domain Models - PS Remoting Setup Results

Domain models for server-level PS remoting preparation results.
"""

from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

from .models.enums import ConnectionMethod


@dataclass
class ServerConnectionProfile:
    """Profile of successful PS remoting connection to a server."""

    server_name: str
    connection_method: ConnectionMethod
    auth_method: str
    successful: bool
    last_successful: datetime
    sql_targets: List[str]  # Names of SQL targets on this server
    port: Optional[int] = None
    custom_options: Optional[dict] = None


@dataclass
class PrepareServerResult:
    """Result of preparing a server for PS remoting."""

    server_name: str
    success: bool
    connection_profile: Optional[ServerConnectionProfile]
    error_message: Optional[str]
    logs: List[str]
    manual_script_path: Optional[str] = None

    @classmethod
    def success_result(
        cls,
        server_name: str,
        connection_profile: ServerConnectionProfile,
        logs: List[str]
    ) -> 'PrepareServerResult':
        """Create a successful result."""
        return cls(
            server_name=server_name,
            success=True,
            connection_profile=connection_profile,
            error_message=None,
            logs=logs
        )

    @classmethod
    def failure_result(
        cls,
        server_name: str,
        error_message: str,
        logs: List[str],
        manual_script_path: Optional[str] = None
    ) -> 'PrepareServerResult':
        """Create a failure result."""
        return cls(
            server_name=server_name,
            success=False,
            connection_profile=None,
            error_message=error_message,
            logs=logs,
            manual_script_path=manual_script_path
        )
