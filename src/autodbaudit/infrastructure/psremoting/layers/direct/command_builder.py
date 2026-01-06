"""Build PowerShell connection commands for direct attempts."""

from typing import Optional

from ...models import AuthMethod, Protocol, ConnectionProfile, CredentialBundle
from ...credentials import CredentialHandler


def build_connection_command(
    profile: ConnectionProfile,
    bundle: CredentialBundle,
    credential_handler: CredentialHandler,
    username_override: str | None = None,
    password_override: str | None = None,
) -> str:
    """Build PowerShell command for a direct connection attempt."""
    server = profile.server_name
    auth = profile.auth_method or "Default"
    port = profile.port or 5985

    cred_lines: list[str] = []
    ps_cred: Optional[str] = None
    if username_override and password_override:
        ps_cred = credential_handler.create_pscredential_from_parts(username_override, password_override)
    else:
        ps_cred = credential_handler.create_pscredential(bundle)
    if ps_cred:
        cred_lines.append(ps_cred)
        cred_lines.append("$cred = $credential")
    else:
        cred_lines.append("$cred = $null")

    session_parts = [
        "$session = New-PSSession",
        f"-ComputerName '{server}'",
        f"-Authentication {auth}",
        f"-Port {port}",
    ]

    if (profile.protocol or "").lower() == Protocol.HTTPS.value:
        session_parts.append("-UseSSL")
        session_parts.append("-SessionOption (New-PSSessionOption -SkipCACheck -SkipCNCheck)")

    if ps_cred:
        session_parts.append("-Credential $cred")

    if str(profile.auth_method).lower() in {AuthMethod.BASIC.value.lower(), AuthMethod.NTLM.value.lower()}:
        session_parts.append("-AllowRedirection")
        session_parts.append("-SessionOption (New-PSSessionOption -NoEncryption -SkipCACheck -SkipCNCheck)")

    session_cmd = " ".join(session_parts)
    tail = "if ($session) { 'Connected' } else { 'Failed' }"
    prelude = "Import-Module Microsoft.PowerShell.Security"
    full_lines = [prelude, *cred_lines, session_cmd, tail]
    return "; ".join(full_lines)
