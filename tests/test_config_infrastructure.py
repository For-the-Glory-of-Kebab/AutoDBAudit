"""
Tests for the config infrastructure layer.

This module tests the repository, manager, and credential manager components.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pydantic import SecretStr

from autodbaudit.domain.config import AuditConfig, Credential, SqlTarget
from autodbaudit.infrastructure.config.credential_manager import CredentialManager
from autodbaudit.infrastructure.config.manager import ConfigManager
from autodbaudit.infrastructure.config.repository import ConfigRepository


class TestConfigRepository:
    """Test cases for ConfigRepository."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = ConfigRepository(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_load_json_file_success(self):
        """Test successful JSON file loading."""
        test_data = {"key": "value", "number": 42}
        json_file = self.temp_dir / "test.json"
        json_file.write_text(json.dumps(test_data))

        result = self.repo.load_json_file("test")
        assert result == test_data

    def test_load_jsonc_file_success(self):
        """Test successful JSONC file loading."""
        test_data = {"key": "value", "number": 42}
        jsonc_file = self.temp_dir / "test.jsonc"
        jsonc_file.write_text(json.dumps(test_data))  # JSONC can be regular JSON

        result = self.repo.load_json_file("test")
        assert result == test_data

    def test_load_json_file_not_found(self):
        """Test file not found error."""
        with pytest.raises(FileNotFoundError):
            self.repo.load_json_file("nonexistent")

    def test_save_json_file(self):
        """Test saving JSON file."""
        test_data = {"key": "value", "number": 42}
        self.repo.save_json_file("test", test_data)

        json_file = self.temp_dir / "test.json"
        assert json_file.exists()

        loaded = json.loads(json_file.read_text())
        assert loaded == test_data

    def test_load_audit_config_success(self):
        """Test successful audit config loading."""
        config_data = {
            "organization": "Test Corp",
            "audit_year": 2024,
            "requirements": {"test": True},
            "output": {"format": "json"}
        }
        json_file = self.temp_dir / "audit_config.json"
        json_file.write_text(json.dumps(config_data))

        config = self.repo.load_audit_config()
        assert config.organization == "Test Corp"
        assert config.audit_year == 2024

    def test_load_sql_targets_success(self):
        """Test successful SQL targets loading."""
        targets_data = {
            "targets": [
                {
                    "name": "server1",
                    "server": "sql01",
                    "auth_type": "sql",
                    "credentials_ref": "creds1"
                },
                {
                    "name": "server2",
                    "server": "sql02",
                    "auth_type": "windows",
                    "credentials_ref": "creds2"
                }
            ]
        }
        json_file = self.temp_dir / "sql_targets.json"
        json_file.write_text(json.dumps(targets_data))

        targets = self.repo.load_sql_targets()
        assert len(targets) == 2
        assert targets[0].name == "server1"
        assert targets[1].name == "server2"

    def test_load_credential_success(self):
        """Test successful credential loading."""
        cred_data = {
            "username": "testuser",
            "password": "testpass"
        }
        cred_dir = self.temp_dir / "credentials"
        cred_dir.mkdir()
        cred_file = cred_dir / "test_cred.json"
        cred_file.write_text(json.dumps(cred_data))

        credential = self.repo.load_credential("test_cred")
        assert credential.username == "testuser"
        assert credential.get_password() == "testpass"


class TestConfigManager:
    """Test cases for ConfigManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = ConfigManager(self.temp_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    @patch('autodbaudit.infrastructure.config.repository.ConfigRepository.load_audit_config')
    def test_load_audit_config_caching(self, mock_load):
        """Test that audit config is cached properly."""
        config = AuditConfig(organization="Test", audit_year=2024, requirements={})
        mock_load.return_value = config

        # First call
        result1 = self.manager.load_audit_config()
        assert result1 == config
        assert mock_load.call_count == 1

        # Second call should use cache
        result2 = self.manager.load_audit_config()
        assert result2 == config
        assert mock_load.call_count == 1  # Still 1

        # Force reload
        result3 = self.manager.load_audit_config(force_reload=True)
        assert result3 == config
        assert mock_load.call_count == 2  # Now 2

    def test_get_enabled_targets(self):
        """Test filtering enabled targets."""
        targets = [
            SqlTarget(name="enabled", server="sql01", auth_type="sql", credentials_ref="creds", enabled=True),
            SqlTarget(name="disabled", server="sql02", auth_type="sql", credentials_ref="creds", enabled=False),
        ]

        with patch.object(self.manager, 'load_sql_targets', return_value=targets):
            enabled = self.manager.get_enabled_targets()
            assert len(enabled) == 1
            assert enabled[0].name == "enabled"

    def test_get_targets_by_tag(self):
        """Test filtering targets by tag."""
        targets = [
            SqlTarget(name="prod", server="sql01", auth_type="sql", credentials_ref="creds", tags=["prod"]),
            SqlTarget(name="dev", server="sql02", auth_type="sql", credentials_ref="creds", tags=["dev"]),
            SqlTarget(name="both", server="sql03", auth_type="sql", credentials_ref="creds", tags=["prod", "dev"]),
        ]

        with patch.object(self.manager, 'load_sql_targets', return_value=targets):
            prod_targets = self.manager.get_targets_by_tag("prod")
            assert len(prod_targets) == 2
            assert {t.name for t in prod_targets} == {"prod", "both"}

    def test_validate_all_configs_success(self):
        """Test successful config validation."""
        config = AuditConfig(organization="Test", audit_year=2024, requirements={})
        targets = [SqlTarget(name="test", server="sql01", auth_type="sql", credentials_ref="creds")]
        credential = Credential(username="user", password=SecretStr("pass"))

        with patch.object(self.manager, 'load_audit_config', return_value=config), \
             patch.object(self.manager, 'load_sql_targets', return_value=targets), \
             patch.object(self.manager, 'get_credential', return_value=credential):

            errors = self.manager.validate_all_configs()
            assert errors == []

    def test_validate_all_configs_with_errors(self):
        """Test config validation with errors."""
        with patch.object(self.manager, 'load_audit_config', side_effect=ValueError("Invalid config")), \
             patch.object(self.manager, 'load_sql_targets', return_value=[]):

            errors = self.manager.validate_all_configs()
            assert len(errors) == 1
            assert "Invalid config" in errors[0]


class TestCredentialManager:
    """Test cases for CredentialManager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo = ConfigRepository(self.temp_dir)
        self.cred_manager = CredentialManager(self.repo, master_password="test_password")

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_encrypt_decrypt_credential(self):
        """Test credential encryption and decryption."""
        credential = Credential(username="testuser", password=SecretStr("testpass123"))

        # Encrypt
        encrypted = self.cred_manager.encrypt_credential(credential)
        assert "encrypted" in encrypted
        assert "data" in encrypted

        # Decrypt
        decrypted = self.cred_manager.decrypt_credential(encrypted)
        assert decrypted.username == "testuser"
        assert decrypted.get_password() == "testpass123"

    def test_decrypt_legacy_credential(self):
        """Test decrypting unencrypted legacy credential."""
        legacy_data = {
            "username": "legacyuser",
            "password": "legacypass"
        }

        decrypted = self.cred_manager.decrypt_credential(legacy_data)
        assert decrypted.username == "legacyuser"
        assert decrypted.get_password() == "legacypass"

    @patch('autodbaudit.infrastructure.config.credential_manager.secrets.token_bytes')
    @patch('pathlib.Path.write_bytes')
    def test_get_or_create_salt(self, mock_write, mock_token):
        """Test salt generation and persistence."""
        mock_token.return_value = b"test_salt_32_bytes_long"

        # First call should generate salt
        salt1 = self.cred_manager._get_or_create_salt()
        assert salt1 == b"test_salt_32_bytes_long"
        assert mock_write.call_count == 1

        # Second call should return cached salt
        salt2 = self.cred_manager._get_or_create_salt()
        assert salt2 == b"test_salt_32_bytes_long"
        assert mock_write.call_count == 1  # Still 1

    def test_migrate_legacy_credentials(self):
        """Test migration of legacy credentials."""
        # Create legacy credential file
        cred_dir = self.temp_dir / "credentials"
        cred_dir.mkdir()
        legacy_file = cred_dir / "legacy.json"
        legacy_file.write_text(json.dumps({
            "username": "legacyuser",
            "password": "legacypass"
        }))

        with patch.object(self.repo, 'list_available_configs', return_value={
            "credential_files": ["legacy.json"]
        }):
            results = self.cred_manager.migrate_legacy_credentials("test_password")

            assert "legacy" in results
            assert results["legacy"] == "migrated"

            # Verify encrypted file was created
            encrypted_file = cred_dir / "legacy.json"
            encrypted_data = json.loads(encrypted_file.read_text())
            assert encrypted_data["encrypted"] is True