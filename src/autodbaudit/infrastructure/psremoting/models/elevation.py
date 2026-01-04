# pylint: disable=missing-module-docstring,line-too-long
from pydantic import BaseModel, Field


class ElevationStatus(BaseModel):
    """
    Current shell elevation status and requirements.
    """

    is_elevated: bool = Field(..., description="Whether current process is elevated")
    elevation_required: bool = Field(default=False, description="Whether elevation is needed for operation")
    can_elevate: bool = Field(default=True, description="Whether elevation is possible")
    elevation_method: str | None = Field(None, description="Method to use for elevation (UAC, runas, etc.)")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
