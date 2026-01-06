"""
Fallback connection strategies for PS remoting.

Exports individual fallback runners for SSH, WMI, PsExec, and RPC along with
shared helpers.
"""

from .ssh import try_ssh_powershell
from .wmi import try_wmi_connection
from .psexec import try_psexec_connection
from .rpc import try_rpc_connection

__all__ = [
    "try_ssh_powershell",
    "try_wmi_connection",
    "try_psexec_connection",
    "try_rpc_connection",
]
