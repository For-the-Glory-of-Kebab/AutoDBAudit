"""
Server Connection Info domain model.

This module defines the ServerConnectionInfo domain entity
containing details about server connections.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import ConnectionMethod, OSType


class ServerConnectionInfo(BaseModel):
    """
    Domain model for server connection information.

    Contains details about how to connect to a target server for preparation.
    """

    server_name: str = Field(..., description="Server hostname or IP")
    os_type: OSType = Field(OSType.UNKNOWN, description="Operating system type")
    available_methods: List[ConnectionMethod] = Field(
        default_factory=list,
        description="Available connection methods"
    )
    preferred_method: Optional[ConnectionMethod] = Field(
        None,
        description="Preferred connection method"
    )
    is_available: bool = Field(False, description="Whether server is currently available")
    last_checked: Optional[str] = Field(None, description="Last availability check timestamp")
    connection_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional connection details"
    )
