# pylint: disable=missing-module-docstring,line-too-long
# pyright: reportMissingImports=false
# pylint: disable=no-name-in-module
from pydantic import BaseModel, Field, ConfigDict

from .profile import ConnectionProfile


class PSSession(BaseModel):
    """
    Active PowerShell remoting session.
    """

    session_id: str = Field(..., description="Unique session identifier")
    server_name: str = Field(..., description="Connected server")
    connection_profile: ConnectionProfile = Field(..., description="Parameters used to establish connection")
    is_elevated: bool = Field(default=False, description="Whether session has elevated privileges")
    created_at: str = Field(..., description="When session was established")

    model_config = ConfigDict(use_enum_values=True)
