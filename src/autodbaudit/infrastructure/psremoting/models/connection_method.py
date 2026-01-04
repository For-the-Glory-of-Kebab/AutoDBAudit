# pylint: disable=missing-module-docstring
from enum import Enum


class ConnectionMethod(Enum):
    """Supported connection methods for PS remoting."""

    POWERSHELL_REMOTING = "powershell_remoting"
    WMI = "wmi"
    PSEXEC = "psexec"
