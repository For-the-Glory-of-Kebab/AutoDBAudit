"""Utility helpers for direct PS remoting attempts."""

import ipaddress
from typing import Any

from ...models import AuthMethod
from ...models import CredentialBundle


def enum_to_value(value: Any):
    """Return enum value or passthrough."""
    return value.value if hasattr(value, "value") else value


def credential_variants(bundle: CredentialBundle) -> list[tuple[str | None, str | None]]:
    """
    Build username/password permutations to exhaust domain/workgroup formats.

    Returns list of (username, password); None entries mean use default bundle creds.
    """
    variants: list[tuple[str | None, str | None]] = []
    win = bundle.windows_explicit or {}
    username = win.get("username")
    password = win.get("password")

    if username and password:
        variants.append((username, password))
        if "\\" in username:
            user_only = username.split("\\", 1)[1]
            variants.append((user_only, password))
        if "@" in username:
            variants.append((username.split("@")[0], password))
    return variants


def is_ip_address(hostname: str) -> bool:
    """Determine if the target is an IP address."""
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False


def auth_priority() -> list[AuthMethod]:
    """
    Preferred auth order: Kerberos -> Negotiate -> NTLM -> CredSSP -> Basic -> Default.
    """
    return [
        AuthMethod.KERBEROS,
        AuthMethod.NEGOTIATE,
        AuthMethod.NTLM,
        AuthMethod.CREDSSP,
        AuthMethod.BASIC,
        AuthMethod.DEFAULT,
    ]
