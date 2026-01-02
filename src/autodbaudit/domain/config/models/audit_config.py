"""
Audit Configuration domain model.

This module defines the AuditConfig domain entity containing
all settings that control how audits are performed.
"""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from autodbaudit.domain.config.audit_settings import AuditSettings


class AuditConfig(BaseModel):
    """
    Domain model for audit configuration.

    Contains all settings that control how audits are performed.
    """

    model_config = ConfigDict(extra="allow")

    organization: str = Field(..., description="Organization name for audit reports")
    audit_year: int = Field(..., description="Audit year")
    requirements: Dict[str, Any] = Field(default_factory=dict, description="Audit requirements configuration")
    output: Dict[str, Any] = Field(default_factory=dict, description="Output configuration")
    global_settings: Dict[str, Any] = Field(
        default_factory=dict,
        description="Global audit settings"
    )

    # OS credentials for PowerShell remoting and WinRM operations
    os_credentials_ref: Optional[str] = Field(
        None,
        description="Reference to OS credentials file for PSRemote/WinRM operations"
    )

    # Dynamic audit settings for timeouts and performance
    audit_settings: AuditSettings = Field(
        default_factory=AuditSettings,
        description="Dynamic audit settings for timeouts and performance tuning"
    )

    @field_validator('audit_year')
    @classmethod
    def validate_audit_year(cls, v: int) -> int:
        """Validate audit year is reasonable."""
        current_year = 2024  # Could be made dynamic
        if v < 2000 or v > current_year + 10:
            raise ValueError(f"Audit year must be between 2000 and {current_year + 10}")
        return v
