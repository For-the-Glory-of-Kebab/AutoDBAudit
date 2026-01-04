# pylint: disable=missing-module-docstring
from enum import Enum


class Protocol(Enum):
    """Supported remoting protocols."""

    HTTP = "http"
    HTTPS = "https"
    SSH = "ssh"
