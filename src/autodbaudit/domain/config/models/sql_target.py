"""
SQL Target domain model.

This module defines the SqlTarget domain entity representing
a SQL Server instance that can be audited.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import AuthType


class SqlTarget(BaseModel):
    """
    Domain model for a SQL Server target.

    Represents a single SQL Server instance that can be audited.
    """

    name: str = Field(..., description="Unique identifier for this target")
    server: str = Field(..., description="SQL Server instance name or IP")
    port: Optional[int] = Field(1433, description="SQL Server port (default 1433)")
    database: Optional[str] = Field(None, description="Default database to connect to")
    auth_type: AuthType = Field(..., description="Authentication method")
    credentials_ref: str = Field(..., description="Reference to credentials file")
    tags: List[str] = Field(default_factory=list, description="Tags for filtering/grouping")
    description: Optional[str] = Field(None, description="Human-readable description")
    enabled: bool = Field(True, description="Whether this target is enabled for auditing")

    @field_validator('server')
    @classmethod
    def validate_server(cls, v: str) -> str:
        """Validate server name format."""
        if not v or not v.strip():
            raise ValueError("Server name cannot be empty")
        return v.strip()

    @field_validator('port')
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        """Validate port number."""
        if v is not None and (v < 1 or v > 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v
