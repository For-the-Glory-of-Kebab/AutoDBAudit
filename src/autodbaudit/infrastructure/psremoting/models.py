"""
PS Remoting Domain Models

Core domain models for PowerShell remoting functionality.
These models define the data structures used throughout the PS remoting infrastructure.
"""

from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class AuthMethod(Enum):
    """Supported PowerShell remoting authentication methods."""

    DEFAULT = "Default"
    KERBEROS = "Kerberos"
    NTLM = "NTLM"
    NEGOTIATE = "Negotiate"
    BASIC = "Basic"
    CREDSsp = "CredSSP"


class Protocol(Enum):
    """Supported remoting protocols."""

    HTTP = "http"
    HTTPS = "https"
    SSH = "ssh"


class CredentialType(Enum):
    """Types of credentials supported for authentication."""

    WINDOWS_INTEGRATED = "windows_integrated"  # Current user context
    WINDOWS_EXPLICIT = "windows_explicit"     # Domain\user + password
    PSCREDENTIAL = "pscredential"             # Pre-created PSCredential object


class ConnectionState(Enum):
    """Possible states of a PS remoting connection."""

    UNKNOWN = "unknown"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"
    REQUIRES_ELEVATION = "requires_elevation"


class ConnectionMethod(Enum):
    """Supported connection methods for PS remoting."""

    POWERSHELL_REMOTING = "powershell_remoting"
    WMI = "wmi"
    PSEXEC = "psexec"


class ConnectionProfile(BaseModel):
    """
    Successful connection parameters for a target server.

    This model stores the parameters that worked for establishing
    PS remoting to a specific server, allowing reuse and avoiding
    repeated discovery attempts.
    """

    id: Optional[int] = Field(None, description="Primary key in persistence store")
    server_name: str = Field(..., description="Target server hostname or IP")
    connection_method: ConnectionMethod = Field(..., description="Connection method that worked")
    auth_method: Optional[str] = Field(None, description="Authentication method that worked")
    protocol: Optional[str] = Field(None, description="Protocol that worked (http/https)")
    port: Optional[int] = Field(None, description="Port that worked")
    credential_type: Optional[str] = Field(None, description="Credential type used for this profile")
    successful: bool = Field(default=False, description="Whether connection was successful")
    last_successful_attempt: Optional[str] = Field(None, description="Timestamp of last successful connection")
    last_attempt: Optional[str] = Field(None, description="Timestamp of last attempt")
    attempt_count: int = Field(default=0, description="Total number of connection attempts")
    sql_targets: List[str] = Field(default_factory=list, description="Associated SQL target names")
    baseline_state: Optional[Dict[str, Any]] = Field(None, description="JSON snapshot of server state before changes")
    current_state: Optional[Dict[str, Any]] = Field(None, description="JSON snapshot of server state after changes")
    created_at: str = Field(..., description="When this profile was first created")
    updated_at: str = Field(..., description="When this profile was last updated")

    class Config:
        use_enum_values = True


class ConnectionAttempt(BaseModel):
    """
    Record of a connection attempt for logging and analysis.

    Tracks all attempts made to connect to a server, successful or failed,
    to provide insights into what works and what doesn't.
    """

    profile_id: Optional[int] = Field(None, description="Reference to connection profile")
    server_name: Optional[str] = Field(None, description="Target server hostname or IP")
    protocol: Optional[str] = Field(None, description="Protocol attempted (http/https)")
    port: Optional[int] = Field(None, description="Port attempted")
    credential_type: Optional[str] = Field(None, description="Credential type used")
    attempted_at: Optional[str] = Field(None, description="Timestamp of attempt")
    attempt_timestamp: Optional[str] = Field(None, description="When the attempt was made")
    layer: Optional[str] = Field(None, description="Layer where attempt was made (direct, client_config, target_config, fallback, manual)")
    connection_method: Optional[ConnectionMethod] = Field(None, description="Connection method attempted")
    auth_method: Optional[str] = Field(None, description="Authentication method tried")
    success: bool = Field(default=False, description="Whether attempt succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="How long the attempt took")
    config_changes: Optional[Dict[str, Any]] = Field(None, description="JSON of configuration changes made")
    rollback_actions: Optional[Dict[str, Any]] = Field(None, description="JSON of actions needed to rollback changes")
    manual_script_path: Optional[str] = Field(None, description="Path to generated manual override script")
    created_at: Optional[str] = Field(None, description="When attempt was recorded")

    class Config:
        use_enum_values = True


class ServerState(BaseModel):
    """
    Snapshot of server state for baseline and current configurations.

    Captures WinRM service settings, firewall rules, trusted hosts,
    network category, registry settings, and other relevant state.
    """

    profile_id: int = Field(..., description="Reference to connection profile")
    state_type: str = Field(..., description="Type of state snapshot (baseline, current)")
    collected_at: str = Field(..., description="When state was collected")

    # WinRM Service
    winrm_service_status: Optional[str] = Field(None, description="WinRM service status")
    winrm_service_startup: Optional[str] = Field(None, description="WinRM service startup type")
    winrm_service_account: Optional[str] = Field(None, description="WinRM service account")

    # Firewall Rules
    winrm_firewall_enabled: Optional[bool] = Field(None, description="WinRM firewall rules enabled")
    winrm_firewall_ports: Optional[List[int]] = Field(None, description="Open WinRM ports")

    # TrustedHosts
    trusted_hosts: Optional[str] = Field(None, description="Current TrustedHosts list")

    # Network Settings
    network_category: Optional[str] = Field(None, description="Network category (Public/Private/Domain)")

    # Registry Settings
    local_account_token_filter: Optional[bool] = Field(None, description="LocalAccountTokenFilterPolicy setting")
    allow_unencrypted: Optional[bool] = Field(None, description="Allow unencrypted traffic")
    auth_basic: Optional[bool] = Field(None, description="Basic authentication enabled")
    auth_kerberos: Optional[bool] = Field(None, description="Kerberos authentication enabled")
    auth_negotiate: Optional[bool] = Field(None, description="Negotiate authentication enabled")
    auth_certificate: Optional[bool] = Field(None, description="Certificate authentication enabled")
    auth_credssp: Optional[bool] = Field(None, description="CredSSP authentication enabled")
    auth_digest: Optional[bool] = Field(None, description="Digest authentication enabled")

    # PowerShell Execution Policy
    execution_policy: Optional[str] = Field(None, description="PowerShell execution policy")

    # UAC Settings
    enable_lua: Optional[bool] = Field(None, description="UAC enabled (enable_lua)")

    # Remote Management
    remote_management_enabled: Optional[bool] = Field(None, description="Remote management enabled")

    # Collected Data
    full_state_json: Optional[Dict[str, Any]] = Field(None, description="Complete JSON snapshot")

    class Config:
        use_enum_values = True


class PSSession(BaseModel):
    """
    Active PowerShell remoting session.

    Represents an established PS remoting session that can be used
    for executing commands on the remote server.
    """

    session_id: str = Field(..., description="Unique session identifier")
    server_name: str = Field(..., description="Connected server")
    connection_profile: ConnectionProfile = Field(..., description="Parameters used to establish connection")
    is_elevated: bool = Field(default=False, description="Whether session has elevated privileges")
    created_at: str = Field(..., description="When session was established")

    class Config:
        use_enum_values = True


class ElevationStatus(BaseModel):
    """
    Current shell elevation status and requirements.

    Provides information about whether the current process has
    administrative privileges and what actions are needed.
    """

    is_elevated: bool = Field(..., description="Whether current process is elevated")
    elevation_required: bool = Field(default=False, description="Whether elevation is needed for operation")
    can_elevate: bool = Field(default=True, description="Whether elevation is possible")
    elevation_method: Optional[str] = Field(None, description="Method to use for elevation (UAC, runas, etc.)")


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

    def is_success(self) -> bool:
        """Check if operation was successful."""
        return self.success

    def get_session(self) -> Optional[PSSession]:
        """Get the established session if successful."""
        return self.session if self.success else None

    def get_error(self) -> Optional[str]:
        """Get error message if failed."""
        return self.error_message if not self.success else None
