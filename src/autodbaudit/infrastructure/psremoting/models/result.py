# pylint: disable=missing-module-docstring,line-too-long
from typing import Optional, List, Dict, Any
# pyright: reportMissingImports=false
# pylint: disable=no-name-in-module
from pydantic import BaseModel, Field, ConfigDict

from .attempt import ConnectionAttempt
from .session import PSSession


class PSRemotingResult(BaseModel):
    """
    Result of a PS remoting operation.

    Uses Railway-oriented programming pattern with success/failure variants.
    """

    success: bool = Field(..., description="Whether operation succeeded")
    session: Optional[PSSession] = Field(None, description="Established session if successful")
    error_message: Optional[str] = Field(None, description="Error details if failed")
    attempts_made: List[ConnectionAttempt] = Field(default_factory=list, description="All attempts made")
    duration_ms: int = Field(default=0, description="Total time taken")

    # Layer 5: Manual override support
    troubleshooting_report: Optional[str] = Field(None, description="Comprehensive troubleshooting report")
    manual_setup_scripts: Optional[List[str]] = Field(None, description="PowerShell scripts for manual setup")
    revert_scripts: Optional[List[str]] = Field(None, description="Scripts to revert all configuration changes")
    successful_permutations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Connection parameter permutations that succeeded"
    )

    def is_success(self) -> bool:
        """Check if operation was successful."""
        return self.success

    def get_session(self) -> Optional[PSSession]:
        """Get the established session if successful."""
        return self.session if self.success else None

    def get_error(self) -> Optional[str]:
        """Get error message if failed."""
        return self.error_message if not self.success else None
    model_config = ConfigDict(use_enum_values=True)


class CommandResult(BaseModel):
    """
    Structured result for executing remote commands/scripts via PS remoting.
    """

    success: bool = Field(..., description="Whether the command succeeded")
    stdout: str = Field("", description="Standard output")
    stderr: str = Field("", description="Standard error")
    exit_code: Optional[int] = Field(None, description="Process exit code")
    duration_ms: int = Field(0, description="Execution duration in milliseconds")
    method_used: Optional[Dict[str, Any]] = Field(
        None, description="Connection parameters used (auth/protocol/port/credential_type/layer)"
    )
    revert_scripts_applied: List[str] = Field(
        default_factory=list, description="Revert scripts applied during execution"
    )
    troubleshooting: Optional[str] = Field(
        None, description="Troubleshooting report if available"
    )
    model_config = ConfigDict(use_enum_values=True)
