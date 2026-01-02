"""
Audit settings domain model for dynamic timeout configuration.

This module defines the audit settings that control timeouts and performance
parameters for the entire application.
"""

from pydantic import BaseModel, Field, field_validator


class AuditTimeouts(BaseModel):
    """
    Timeout settings for different operations.

    Allows dynamic tuning based on environment, network, and hardware performance.
    """

    powershell_command_timeout: int = Field(
        default=30,
        description="Timeout in seconds for PowerShell remoting commands",
        ge=5,
        le=300
    )

    tsql_query_timeout: int = Field(
        default=60,
        description="Timeout in seconds for T-SQL queries",
        ge=10,
        le=600
    )

    connection_test_timeout: int = Field(
        default=10,
        description="Timeout in seconds for connection tests",
        ge=1,
        le=60
    )

    os_detection_timeout: int = Field(
        default=15,
        description="Timeout in seconds for OS detection",
        ge=5,
        le=120
    )

    @field_validator('powershell_command_timeout', 'tsql_query_timeout')
    @classmethod
    def validate_reasonable_timeouts(cls, v: int, info) -> int:
        """Validate that timeouts are reasonable for the operation type."""
        field_name = info.field_name
        if field_name == 'powershell_command_timeout' and v > 120:
            # Warn about very long PowerShell timeouts
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("PowerShell timeout of %s is very high - consider network conditions", v)
        elif field_name == 'tsql_query_timeout' and v > 300:
            # Warn about very long T-SQL timeouts
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("T-SQL timeout of %s is very high - consider query complexity", v)
        return v


class AuditSettings(BaseModel):
    """
    Comprehensive audit settings for the application.

    Controls all performance and timeout parameters dynamically.
    """

    timeouts: AuditTimeouts = AuditTimeouts()

    require_elevated_shell: bool = Field(
        default=False,
        description="Whether to require elevated shell for operations"
    )

    enable_parallel_processing: bool = Field(
        default=True,
        description="Whether to run prepare and persistence operations in parallel"
    )

    max_parallel_targets: int = Field(
        default=5,
        description="Maximum number of targets to process in parallel",
        ge=1,
        le=20
    )

    enable_fallback_scripts: bool = Field(
        default=True,
        description="Whether to generate PowerShell fallback scripts when remoting fails"
    )

    @property
    def is_elevated_shell_required(self) -> bool:
        """Check if elevated shell is required for current operations."""
        return self.require_elevated_shell

    def get_timeout_for_operation(self, operation: str) -> int:
        """
        Get the appropriate timeout for a specific operation.

        Args:
            operation: The operation type ('powershell', 'tsql', 'connection', 'os_detection')

        Returns:
            Timeout in seconds
        """
        match operation:
            case 'powershell':
                return self.timeouts.powershell_command_timeout  # type: ignore
            case 'tsql':
                return self.timeouts.tsql_query_timeout  # type: ignore
            case 'connection':
                return self.timeouts.connection_test_timeout  # type: ignore
            case 'os_detection':
                return self.timeouts.os_detection_timeout  # type: ignore
            case _:
                return 30  # Default fallback
