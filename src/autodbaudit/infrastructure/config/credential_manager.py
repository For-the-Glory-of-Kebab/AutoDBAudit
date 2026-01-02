"""
Credential manager for secure credential operations.

This module provides secure handling of database credentials with
encryption/decryption capabilities and secure storage patterns.
"""

import base64
import hashlib
import json
import logging
import secrets
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import SecretStr

from autodbaudit.domain.config.models import Credential
from .repository import ConfigRepository  # pylint: disable=relative-beyond-top-level

logger = logging.getLogger(__name__)


class CredentialManager:
    """
    Manager for secure credential operations.

    Provides encryption/decryption of credentials and secure storage patterns.
    Uses PBKDF2 key derivation and Fernet symmetric encryption.
    """

    # Key derivation parameters
    SALT_LENGTH = 32
    ITERATIONS = 100000
    KEY_LENGTH = 32

    def __init__(self, repository: ConfigRepository, master_password: Optional[str] = None):
        """
        Initialize the credential manager.

        Args:
            repository: Config repository for file operations
            master_password: Master password for encryption (optional, will prompt if needed)
        """
        self.repository = repository
        self.master_password = master_password
        self._encryption_key: Optional[bytes] = None
        self._salt: Optional[bytes] = None

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2.

        Args:
            password: Master password
            salt: Salt for key derivation

        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _get_or_create_salt(self) -> bytes:
        """
        Get existing salt or create a new one.

        Returns:
            Salt bytes
        """
        if self._salt is not None:
            return self._salt

        # Try to load existing salt
        salt_file = self.repository.config_dir / "credentials" / ".salt"
        if salt_file.exists():
            try:
                self._salt = salt_file.read_bytes()
                return self._salt
            except Exception as e:
                logger.warning("Failed to load salt file: %s", e)

        # Create new salt
        self._salt = secrets.token_bytes(self.SALT_LENGTH)
        try:
            salt_file.parent.mkdir(parents=True, exist_ok=True)
            salt_file.write_bytes(self._salt)
            logger.info("Created new salt file")
        except Exception as e:
            logger.warning("Failed to save salt file: %s", e)

        return self._salt

    def _get_encryption_key(self) -> bytes:
        """
        Get or create the encryption key.

        Returns:
            Encryption key for Fernet

        Raises:
            ValueError: If master password is not available
        """
        if self._encryption_key is not None:
            return self._encryption_key

        if not self.master_password:
            raise ValueError("Master password required for credential encryption")

        salt = self._get_or_create_salt()
        self._encryption_key = self._derive_key(self.master_password, salt)
        return self._encryption_key

    def encrypt_credential(self, credential: Credential) -> Dict[str, Any]:
        """
        Encrypt a credential for storage.

        Args:
            credential: Credential domain model to encrypt

        Returns:
            Dictionary with encrypted credential data

        Raises:
            ValueError: If encryption fails
        """
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)

            # Encrypt the data
            data = {
                "username": credential.username,
                "password": credential.get_password()
            }

            json_data = str(data).encode()
            encrypted_data = fernet.encrypt(json_data)

            return {
                "encrypted": True,
                "data": base64.b64encode(encrypted_data).decode(),
                "salt_hash": hashlib.sha256(self._get_or_create_salt()).hexdigest()
            }
        except Exception as e:
            logger.error("Failed to encrypt credential: %s", e)
            raise ValueError(f"Credential encryption failed: {e}") from e

    def decrypt_credential(self, encrypted_data: Dict[str, str]) -> Credential:
        """
        Decrypt an encrypted credential.

        Args:
            encrypted_data: Dictionary with encrypted credential data

        Returns:
            Decrypted Credential domain model

        Raises:
            ValueError: If decryption fails or data is invalid
        """
        try:
            if not encrypted_data.get("encrypted", False):
                # Handle unencrypted legacy format
                return Credential(
                    username=encrypted_data["username"],
                    password=SecretStr(encrypted_data["password"])
                )

            key = self._get_encryption_key()
            fernet = Fernet(key)

            # Verify salt hash if present
            if "salt_hash" in encrypted_data:
                expected_hash = hashlib.sha256(self._get_or_create_salt()).hexdigest()
                if encrypted_data["salt_hash"] != expected_hash:
                    raise ValueError("Salt hash mismatch - credential may be corrupted")

            # Decrypt the data
            encrypted_bytes = base64.b64decode(encrypted_data["data"])
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            decrypted_str = decrypted_bytes.decode()

            # Parse the decrypted JSON data safely
            try:
                data = json.loads(decrypted_str)
            except json.JSONDecodeError:
                # Fallback for legacy format that might not be proper JSON
                # Extract username and password from string representation
                import ast
                data = ast.literal_eval(decrypted_str)

            return Credential(
                username=data["username"],
                password=SecretStr(data["password"])
            )
        except Exception as e:
            logger.error("Failed to decrypt credential: %s", e)
            raise ValueError(f"Credential decryption failed: {e}") from e

    def save_encrypted_credential(self, cred_ref: str, credential: Credential) -> None:
        """
        Save a credential in encrypted form.

        Args:
            cred_ref: Reference name for the credential
            credential: Credential to save

        Raises:
            ValueError: If saving fails
        """
        try:
            encrypted_data = self.encrypt_credential(credential)
            self.repository.save_json_file(f"credentials/{cred_ref}", encrypted_data)
            logger.info("Saved encrypted credential: %s", cred_ref)
        except Exception as e:
            logger.error("Failed to save encrypted credential '%s': %s", cred_ref, e)
            raise ValueError(f"Failed to save credential '{cred_ref}': {e}") from e

    def load_decrypted_credential(self, cred_ref: str) -> Credential:
        """
        Load and decrypt a credential.

        Args:
            cred_ref: Reference name for the credential

        Returns:
            Decrypted Credential domain model

        Raises:
            ValueError: If loading or decryption fails
        """
        try:
            encrypted_data = self.repository.load_json_file(f"credentials/{cred_ref}")
            credential = self.decrypt_credential(encrypted_data)
            logger.debug("Loaded decrypted credential: %s", cred_ref)
            return credential
        except Exception as e:
            logger.error("Failed to load decrypted credential '%s': %s", cred_ref, e)
            raise ValueError(f"Failed to load credential '{cred_ref}': {e}") from e

    def migrate_legacy_credentials(self, master_password: str) -> Dict[str, str]:
        """
        Migrate legacy unencrypted credentials to encrypted format.

        Args:
            master_password: Master password for encryption

        Returns:
            Dictionary mapping credential refs to migration status
        """
        self.master_password = master_password
        results = {}

        try:
            available_configs = self.repository.list_available_configs()
            credential_files = available_configs.get("credential_files", [])

            for cred_file in credential_files:
                cred_ref = cred_file.replace(".json", "")
                try:
                    # Try to load as unencrypted first
                    cred_data = self.repository.load_json_file(f"credentials/{cred_ref}")
                    if not cred_data.get("encrypted", False):
                        # This is a legacy unencrypted credential
                        credential = Credential(
                            username=cred_data.get("username", cred_data.get("user", "")),
                            password=SecretStr(cred_data.get("password", ""))
                        )
                        self.save_encrypted_credential(cred_ref, credential)
                        results[cred_ref] = "migrated"
                        logger.info("Migrated legacy credential: %s", cred_ref)
                    else:
                        results[cred_ref] = "already_encrypted"
                except Exception as e:
                    results[cred_ref] = f"migration_failed: {e}"
                    logger.error("Failed to migrate credential '%s': %s", cred_ref, e)

        except Exception as e:
            logger.error("Credential migration failed: %s", e)
            results["error"] = str(e)

        return results
