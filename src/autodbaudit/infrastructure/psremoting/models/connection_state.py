# pylint: disable=missing-module-docstring
from enum import Enum


class ConnectionState(Enum):
    """Possible states of a PS remoting connection."""

    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    REQUIRES_ELEVATION = "requires_elevation"
