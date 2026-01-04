# pylint: disable=missing-module-docstring
from enum import Enum


class AuthMethod(Enum):
    """Supported PowerShell remoting authentication methods."""

    DEFAULT = "Default"
    KERBEROS = "Kerberos"
    NTLM = "NTLM"
    NEGOTIATE = "Negotiate"
    BASIC = "Basic"
    CREDSSP = "CredSSP"
