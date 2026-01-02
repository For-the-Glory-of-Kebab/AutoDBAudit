"""
Type aliases for configuration domain.

This module defines type aliases for better readability and maintainability.
"""

from typing import Dict, List

from .models.credential import Credential
from .models.prepare_result import PrepareResult
from .models.server_connection_info import ServerConnectionInfo
from .models.sql_target import SqlTarget

# Type aliases for collections
SqlTargets = List[SqlTarget]
Credentials = Dict[str, Credential]
ServerConnections = Dict[str, ServerConnectionInfo]
PrepareResults = List[PrepareResult]

__all__ = [
    "Credentials",
    "PrepareResults",
    "ServerConnections",
    "SqlTargets",
]
