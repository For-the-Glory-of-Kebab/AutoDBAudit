# pylint: disable=missing-module-docstring,line-too-long
from typing import Optional, Dict, Any, List
# pyright: reportMissingImports=false
# pylint: disable=no-name-in-module
from pydantic import BaseModel, Field, ConfigDict


class ServerState(BaseModel):
    """
    Snapshot of server state for baseline and current configurations.
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

    model_config = ConfigDict(use_enum_values=True)
