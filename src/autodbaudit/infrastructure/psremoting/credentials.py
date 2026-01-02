"""
Credential Handler for PS Remoting

Handles various credential types and converts them to PowerShell-compatible formats.
Supports Windows integrated, explicit credentials, and PSCredential objects.
"""

import base64
from typing import Optional, Dict, Any, Union
import platform

from .models import CredentialType, CredentialBundle


class CredentialHandler:
    """
    Handles credential preparation and conversion for PS remoting.

    This class manages different credential formats and converts them
    to PowerShell-compatible PSCredential objects when needed.
    """

    def __init__(self):
        self._is_windows = platform.system() == "Windows"

    def prepare_credentials(self, credentials: Dict[str, Any]) -> CredentialBundle:
        """
        Prepare credentials from configuration for PS remoting use.

        Args:
            credentials: Raw credential configuration

        Returns:
            CredentialBundle: Processed credentials ready for use
        """
        bundle = CredentialBundle(windows_explicit=None, pscredential=None)

        # Extract Windows explicit credentials
        if 'windows_credentials' in credentials:
            windows_creds = credentials['windows_credentials']
            if isinstance(windows_creds, dict):
                # Look for domain admin or similar privileged account
                privileged_accounts = ['domain_admin', 'admin', 'administrator']
                for account_key in privileged_accounts:
                    if account_key in windows_creds:
                        bundle.windows_explicit = windows_creds[account_key]
                        break

        # If no explicit credentials, check for PSCredential
        if not bundle.has_credentials() and 'pscredential' in credentials:
            bundle.pscredential = credentials['pscredential']

        return bundle

    def create_pscredential(self, bundle: CredentialBundle) -> Optional[str]:
        """
        Create a PowerShell PSCredential object from credential bundle.

        Args:
            bundle: Credential bundle to convert

        Returns:
            str: PowerShell command to create PSCredential, or None if not possible
        """
        if not self._is_windows:
            return None

        if bundle.windows_explicit:
            return self._create_pscredential_from_explicit(bundle.windows_explicit)
        elif bundle.pscredential:
            return bundle.pscredential

        return None

    def get_credential_type(self, bundle: CredentialBundle) -> CredentialType:
        """
        Determine the credential type from a bundle.

        Args:
            bundle: Credential bundle to analyze

        Returns:
            CredentialType: The type of credentials available
        """
        if bundle.windows_explicit:
            return CredentialType.WINDOWS_EXPLICIT
        elif bundle.pscredential:
            return CredentialType.PSCREDENTIAL
        else:
            return CredentialType.WINDOWS_INTEGRATED

    def validate_credentials(self, bundle: CredentialBundle) -> bool:
        """
        Validate that credentials are properly formatted.

        Args:
            bundle: Credential bundle to validate

        Returns:
            bool: True if credentials appear valid
        """
        if bundle.windows_explicit:
            creds = bundle.windows_explicit
            return (
                isinstance(creds, dict) and
                'username' in creds and
                'password' in creds and
                bool(creds['username']) and
                bool(creds['password'])
            )

        if bundle.pscredential:
            return bool(bundle.pscredential.strip())

        # Windows integrated doesn't need validation
        return True

    def _create_pscredential_from_explicit(self, creds: Dict[str, str]) -> str:
        """
        Create PSCredential from explicit username/password.

        Args:
            creds: Dictionary with 'username' and 'password' keys

        Returns:
            str: PowerShell command to create PSCredential
        """
        username = creds['username']
        password = creds['password']

        # Escape single quotes in password for PowerShell
        escaped_password = password.replace("'", "''")

        return "\n".join([
            f"$securePassword = ConvertTo-SecureString '{escaped_password}' -AsPlainText -Force",
            f"$credential = New-Object System.Management.Automation.PSCredential('{username}', $securePassword)",
            "$credential"
        ])

    def create_secure_credential_store(self, bundle: CredentialBundle) -> Dict[str, Any]:
        """
        Create a secure representation of credentials for storage.

        Args:
            bundle: Credential bundle to secure

        Returns:
            dict: Secure credential representation (passwords encrypted)
        """
        secure_bundle = {}

        if bundle.windows_explicit:
            secure_bundle['windows_explicit'] = {
                'username': bundle.windows_explicit['username'],
                'password': self._encrypt_password(bundle.windows_explicit['password'])
            }

        if bundle.pscredential:
            secure_bundle['pscredential'] = bundle.pscredential

        return secure_bundle

    def _encrypt_password(self, password: str) -> str:
        """
        Encrypt a password for secure storage.

        Args:
            password: Plain text password

        Returns:
            str: Encrypted password (base64 encoded for simplicity)
        """
        # In production, use proper encryption like Fernet
        # For now, use base64 as a placeholder
        return base64.b64encode(password.encode()).decode()

    def decrypt_password(self, encrypted: str) -> str:
        """
        Decrypt a previously encrypted password.

        Args:
            encrypted: Encrypted password

        Returns:
            str: Plain text password
        """
        # In production, use proper decryption
        # For now, decode base64
        try:
            return base64.b64decode(encrypted.encode()).decode()
        except Exception:
            return encrypted  # Return as-is if not encrypted
