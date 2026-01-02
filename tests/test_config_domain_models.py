"""
Comprehensive tests for the config domain models.

This module provides thorough testing for all domain models in the config system,
including validation, serialization, and business logic.
"""

import pytest
from pydantic import ValidationError

from autodbaudit.domain.config import (
    AuthType,
    AuditConfig,
    ConnectionMethod,
    Credential,
    OSType,
    PrepareResult,
    ServerConnectionInfo,
    SqlTarget
)


class TestSqlTarget:
    """Test cases for SqlTarget domain model."""

    def test_valid_sql_target_creation(self):
        """Test creating a valid SQL target."""
        target = SqlTarget(
            name="test_server",
            server="sql01.company.com",
            port=1433,
            database="master",
            auth_type=AuthType.SQL,
            credentials_ref="sql_creds",
            tags=["production", "critical"],
            description="Production SQL Server"
        )

        assert target.name == "test_server"
        assert target.server == "sql01.company.com"
        assert target.port == 1433
        assert target.database == "master"
        assert target.auth_type == AuthType.SQL
        assert target.credentials_ref == "sql_creds"
        assert target.tags == ["production", "critical"]
        assert target.description == "Production SQL Server"
        assert target.enabled is True

    def test_sql_target_default_values(self):
        """Test default values for SQL target."""
        target = SqlTarget(
            name="minimal",
            server="sql01",
            auth_type=AuthType.WINDOWS,
            credentials_ref="win_creds"
        )

        assert target.port == 1433
        assert target.database is None
        assert target.tags == []
        assert target.description is None
        assert target.enabled is True

    def test_sql_target_validation_server_required(self):
        """Test that server is required and cannot be empty."""
        with pytest.raises(ValidationError):
            SqlTarget(
                name="test",
                server="",
                auth_type=AuthType.SQL,
                credentials_ref="creds"
            )

    def test_sql_target_validation_port_range(self):
        """Test port validation."""
        # Valid ports
        SqlTarget(name="test", server="sql01", port=1, auth_type=AuthType.SQL, credentials_ref="creds")
        SqlTarget(name="test", server="sql01", port=65535, auth_type=AuthType.SQL, credentials_ref="creds")

        # Invalid ports
        with pytest.raises(ValidationError):
            SqlTarget(name="test", server="sql01", port=0, auth_type=AuthType.SQL, credentials_ref="creds")

        with pytest.raises(ValidationError):
            SqlTarget(name="test", server="sql01", port=65536, auth_type=AuthType.SQL, credentials_ref="creds")

    def test_sql_target_serialization(self):
        """Test JSON serialization of SQL target."""
        target = SqlTarget(
            name="test",
            server="sql01",
            auth_type=AuthType.SQL,
            credentials_ref="creds"
        )

        data = target.model_dump(mode='json')
        assert data["name"] == "test"
        assert data["auth_type"] == "sql"  # enum values
        assert data["enabled"] is True


class TestAuditConfig:
    """Test cases for AuditConfig domain model."""

    def test_valid_audit_config_creation(self):
        """Test creating a valid audit config."""
        config = AuditConfig(
            organization="Test Corp",
            audit_year=2024,
            requirements={"cis": "v1.0", "sox": True},
            output={"format": "excel", "path": "./reports"},
            global_settings={"timeout": 30}
        )

        assert config.organization == "Test Corp"
        assert config.audit_year == 2024
        assert config.requirements == {"cis": "v1.0", "sox": True}
        assert config.output == {"format": "excel", "path": "./reports"}
        assert config.global_settings == {"timeout": 30}

    def test_audit_config_validation_year_range(self):
        """Test audit year validation."""
        # Valid years
        AuditConfig(organization="Test", audit_year=2000, requirements={})
        AuditConfig(organization="Test", audit_year=2030, requirements={})

        # Invalid years
        with pytest.raises(ValidationError):
            AuditConfig(organization="Test", audit_year=1999, requirements={})

        with pytest.raises(ValidationError):
            AuditConfig(organization="Test", audit_year=2041, requirements={})

    def test_audit_config_extra_fields_allowed(self):
        """Test that extra fields are allowed in audit config."""
        config = AuditConfig(
            organization="Test",
            audit_year=2024,
            requirements={},
            custom_field="allowed"
        )

        assert config.custom_field == "allowed"


class TestCredential:
    """Test cases for Credential domain model."""

    def test_valid_credential_creation(self):
        """Test creating a valid credential."""
        from pydantic import SecretStr

        cred = Credential(
            username="testuser",
            password=SecretStr("testpass123")
        )

        assert cred.username == "testuser"
        assert cred.get_password() == "testpass123"

    def test_credential_validation_username_required(self):
        """Test that username is required and cannot be empty."""
        from pydantic import SecretStr

        with pytest.raises(ValidationError):
            Credential(username="", password=SecretStr("pass"))

        with pytest.raises(ValidationError):
            Credential(username="   ", password=SecretStr("pass"))

    def test_credential_password_masking(self):
        """Test that password is masked in JSON output."""
        from pydantic import SecretStr

        cred = Credential(username="user", password=SecretStr("secret"))
        json_str = cred.model_dump_json()

        # The password field should be masked in the JSON string
        assert '"password":"***"' in json_str


class TestServerConnectionInfo:
    """Test cases for ServerConnectionInfo domain model."""

    def test_valid_connection_info_creation(self):
        """Test creating valid server connection info."""
        info = ServerConnectionInfo(
            server_name="sql01",
            os_type=OSType.WINDOWS,
            available_methods=[ConnectionMethod.POWERSHELL_REMOTING, ConnectionMethod.WINRM],
            preferred_method=ConnectionMethod.POWERSHELL_REMOTING,
            is_available=True,
            last_checked="2024-01-01T12:00:00",
            connection_details={"port": 1433}
        )

        assert info.server_name == "sql01"
        assert info.os_type == OSType.WINDOWS
        assert info.available_methods == [ConnectionMethod.POWERSHELL_REMOTING, ConnectionMethod.WINRM]
        assert info.preferred_method == ConnectionMethod.POWERSHELL_REMOTING
        assert info.is_available is True
        assert info.last_checked == "2024-01-01T12:00:00"
        assert info.connection_details == {"port": 1433}


class TestPrepareResult:
    """Test cases for PrepareResult domain model."""

    def test_success_result_creation(self):
        """Test creating a successful prepare result."""
        target = SqlTarget(name="test", server="sql01", auth_type=AuthType.SQL, credentials_ref="creds")
        connection_info = ServerConnectionInfo(
            server_name="sql01",
            os_type=OSType.WINDOWS,
            available_methods=[ConnectionMethod.POWERSHELL_REMOTING],
            preferred_method=ConnectionMethod.POWERSHELL_REMOTING,
            is_available=True
        )

        result = PrepareResult.success_result(target, connection_info, ["Log 1", "Log 2"])

        assert result.success is True
        assert result.target == target
        assert result.connection_info == connection_info
        assert result.logs == ["Log 1", "Log 2"]
        assert result.error_message is None

    def test_failure_result_creation(self):
        """Test creating a failed prepare result."""
        target = SqlTarget(name="test", server="sql01", auth_type=AuthType.SQL, credentials_ref="creds")

        result = PrepareResult.failure_result(target, "Connection failed", ["Error log"])

        assert result.success is False
        assert result.target == target
        assert result.connection_info is None
        assert result.error_message == "Connection failed"
        assert result.logs == ["Error log"]


class TestEnums:
    """Test cases for enum values and serialization."""

    def test_auth_type_enum_values(self):
        """Test AuthType enum values."""
        assert AuthType.WINDOWS.value == "windows"
        assert AuthType.SQL.value == "sql"

    def test_os_type_enum_values(self):
        """Test OSType enum values."""
        assert OSType.WINDOWS.value == "windows"
        assert OSType.LINUX.value == "linux"
        assert OSType.UNKNOWN.value == "unknown"

    def test_connection_method_enum_values(self):
        """Test ConnectionMethod enum values."""
        assert ConnectionMethod.POWERSHELL_REMOTING.value == "powershell_remoting"
        assert ConnectionMethod.SSH.value == "ssh"
        assert ConnectionMethod.WINRM.value == "winrm"
        assert ConnectionMethod.DIRECT.value == "direct"

    def test_enum_serialization(self):
        """Test that enums serialize to their values."""
        target = SqlTarget(
            name="test",
            server="sql01",
            auth_type=AuthType.SQL,
            credentials_ref="creds"
        )

        data = target.model_dump(mode='json')
        assert data["auth_type"] == "sql"