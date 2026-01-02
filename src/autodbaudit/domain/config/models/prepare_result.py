"""
Prepare Result domain model.

This module defines the PrepareResult domain entity for
handling prepare operation outcomes using Railway-oriented programming.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .server_connection_info import ServerConnectionInfo
from .sql_target import SqlTarget


class PrepareResult(BaseModel):
    """
    Result model for prepare operations.

    Uses Railway-oriented programming pattern for success/failure handling.
    """

    success: bool = Field(..., description="Whether the operation succeeded")
    target: SqlTarget = Field(..., description="The target that was prepared")
    connection_info: Optional[ServerConnectionInfo] = Field(
        None,
        description="Connection information if successful"
    )
    error_message: Optional[str] = Field(None, description="Error message if failed")
    logs: List[str] = Field(default_factory=list, description="Operation logs")

    @classmethod
    def success_result(
        cls,
        target: SqlTarget,
        connection_info: ServerConnectionInfo,
        logs: Optional[List[str]] = None
    ) -> 'PrepareResult':
        """Create a successful prepare result."""
        return cls(
            success=True,
            target=target,
            connection_info=connection_info,
            logs=logs or []
        )

    @classmethod
    def failure_result(
        cls,
        target: SqlTarget,
        error_message: str,
        logs: Optional[List[str]] = None
    ) -> 'PrepareResult':
        """Create a failed prepare result."""
        return cls(
            success=False,
            target=target,
            error_message=error_message,
            logs=logs or []
        )
