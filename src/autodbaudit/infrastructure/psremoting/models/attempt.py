# pylint: disable=missing-module-docstring,line-too-long
from typing import Optional, Dict, Any
# pyright: reportMissingImports=false
# pylint: disable=no-name-in-module
from pydantic import BaseModel, Field, ConfigDict

from .connection_method import ConnectionMethod


class ConnectionAttempt(BaseModel):
    """
    Record of a connection attempt for logging and analysis.

    Tracks all attempts made to connect to a server, successful or failed.
    """

    profile_id: Optional[int] = Field(None, description="Reference to connection profile")
    server_name: Optional[str] = Field(None, description="Target server hostname or IP")
    protocol: Optional[str] = Field(None, description="Protocol attempted (http/https)")
    port: Optional[int] = Field(None, description="Port attempted")
    credential_type: Optional[str] = Field(None, description="Credential type used")
    attempted_at: Optional[str] = Field(None, description="Timestamp of attempt")
    attempt_timestamp: Optional[str] = Field(None, description="When the attempt was made")
    layer: Optional[str] = Field(None, description="Layer where attempt was made (direct, client_config, target_config, fallback, manual)")
    connection_method: Optional[ConnectionMethod] = Field(None, description="Connection method attempted")
    auth_method: Optional[str] = Field(None, description="Authentication method tried")
    success: bool = Field(default=False, description="Whether attempt succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="How long the attempt took")
    config_changes: Optional[Dict[str, Any]] = Field(None, description="JSON of configuration changes made")
    rollback_actions: Optional[Dict[str, Any]] = Field(None, description="JSON of actions needed to rollback changes")
    manual_script_path: Optional[str] = Field(None, description="Path to generated manual override script")
    created_at: Optional[str] = Field(None, description="When attempt was recorded")

    model_config = ConfigDict(use_enum_values=True)
