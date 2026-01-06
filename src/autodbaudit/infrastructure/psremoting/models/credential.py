# pylint: disable=missing-module-docstring,line-too-long
from enum import Enum
from typing import Optional, Dict
# pyright: reportMissingImports=false
# pylint: disable=no-name-in-module
from pydantic import BaseModel, Field, ConfigDict


class CredentialType(Enum):
    """Types of credentials supported for authentication."""

    WINDOWS_INTEGRATED = "windows_integrated"  # Current user context
    WINDOWS_EXPLICIT = "windows_explicit"     # Domain\user + password
    PSCREDENTIAL = "pscredential"             # Pre-created PSCredential object


class CredentialBundle(BaseModel):
    """
    Bundle of credentials for different authentication scenarios.

    Contains all credential types that might be needed for
    connecting to a target server.
    """

    windows_explicit: Optional[Dict[str, str]] = Field(None, description="Domain\\user and password")
    pscredential: Optional[str] = Field(None, description="Serialized PSCredential object")

    def has_credentials(self) -> bool:
        """Check if any credentials are available."""
        return self.windows_explicit is not None or self.pscredential is not None

    model_config = ConfigDict(use_enum_values=True)
