"""
SQL Target domain model.

This module defines the SqlTarget domain entity representing
a SQL Server instance that can be audited.
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .enums import AuthType


class TargetMetadata(BaseModel):
    """Optional metadata for a SQL target."""

    model_config = ConfigDict(extra="ignore")

    tags: List[str] = Field(default_factory=list, description="Tags for filtering/grouping")
    ip_address: Optional[str] = Field(None, description="Optional IP metadata for reporting")
    description: Optional[str] = Field(None, description="Human-readable description")


class SqlTarget(BaseModel):
    """
    Domain model for a SQL Server target.

    Represents a single SQL Server instance that can be audited.
    """

    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    id: str = Field(..., description="Unique identifier/alias for this target", alias="id")
    name: str = Field(..., description="Human-readable display name (Unicode supported)")
    server: str = Field(..., description="SQL Server instance name or IP")
    instance: Optional[str] = Field(None, description="Named instance (null for default)")
    port: Optional[int] = Field(1433, description="SQL Server port (default 1433)")
    database: Optional[str] = Field(None, description="Default database to connect to")
    auth_type: AuthType = Field(..., description="Authentication method", alias="auth")
    credentials_ref: Optional[str] = Field(None, description="Reference to SQL credentials file", alias="credential_file")
    username: Optional[str] = Field(None, description="Explicit username (if not using credential file)")
    os_credentials_ref: Optional[str] = Field(None, description="Reference to OS credentials file", alias="os_credential_file")
    connect_timeout: int = Field(30, description="Seconds to wait for SQL connection")
    enabled: bool = Field(True, description="Whether this target is enabled for auditing")
    metadata: TargetMetadata = Field(default_factory=TargetMetadata, description="Optional metadata")

    @field_validator("auth_type", mode="before")
    @classmethod
    def normalize_auth(cls, v):
        """Map legacy auth strings to enum."""
        if isinstance(v, str) and v.lower() == "integrated":
            return AuthType.WINDOWS
        return v

    @field_validator("server")
    @classmethod
    def validate_server(cls, v: str) -> str:
        """Validate server name format."""
        if not v or not v.strip():
            raise ValueError("Server name cannot be empty")
        return v.strip()

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: Optional[int]) -> Optional[int]:
        """Validate port number."""
        if v is not None and (v < 1 or v > 65535):
            raise ValueError("Port must be between 1 and 65535")
        return v
