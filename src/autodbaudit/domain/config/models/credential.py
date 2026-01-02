"""
Credential domain model.

This module defines the Credential domain entity for securely
handling database credentials.
"""

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class Credential(BaseModel):
    """
    Domain model for database credentials.

    Securely handles username/password combinations.
    """

    model_config = ConfigDict(
        json_encoders={
            SecretStr: lambda v: "***"  # Mask password in JSON output
        }
    )

    username: str = Field(..., description="Database username")
    password: SecretStr = Field(..., description="Database password")

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username is not empty."""
        if not v or not v.strip():
            raise ValueError("Username cannot be empty")
        return v.strip()

    def get_password(self) -> str:
        """Get the plain text password."""
        return self.password.get_secret_value()  # pylint: disable=no-member
