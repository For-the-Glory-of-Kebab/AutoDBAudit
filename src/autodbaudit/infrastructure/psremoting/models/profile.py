# pylint: disable=missing-module-docstring,line-too-long
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from .connection_method import ConnectionMethod


class ConnectionProfile(BaseModel):
    """
    Successful connection parameters for a target server.

    Stores parameters that worked for establishing PS remoting to a specific server.
    """

    id: Optional[int] = Field(None, description="Primary key in persistence store")
    server_name: str = Field(..., description="Target server hostname or IP")
    connection_method: ConnectionMethod = Field(..., description="Connection method that worked")
    auth_method: Optional[str] = Field(None, description="Authentication method that worked")
    protocol: Optional[str] = Field(None, description="Protocol that worked (http/https)")
    port: Optional[int] = Field(None, description="Port that worked")
    credential_type: Optional[str] = Field(None, description="Credential type used for this profile")
    successful: bool = Field(default=False, description="Whether connection was successful")
    last_successful_attempt: Optional[str] = Field(None, description="Timestamp of last successful connection")
    last_attempt: Optional[str] = Field(None, description="Timestamp of last attempt")
    attempt_count: int = Field(default=0, description="Total number of connection attempts")
    sql_targets: List[str] = Field(default_factory=list, description="Associated SQL target names")
    baseline_state: Optional[Dict[str, Any]] = Field(None, description="JSON snapshot of server state before changes")
    current_state: Optional[Dict[str, Any]] = Field(None, description="JSON snapshot of server state after changes")
    created_at: str = Field(..., description="When this profile was first created")
    updated_at: str = Field(..., description="When this profile was last updated")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
