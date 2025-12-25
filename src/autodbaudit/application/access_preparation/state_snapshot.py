"""
State Snapshot Module.

Captures and restores complete machine state for non-destructive
access preparation with exact revert capability.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class ServiceState:
    """Windows service state."""

    name: str
    status: Literal["Running", "Stopped", "Paused", "Unknown"]
    startup_type: Literal["Automatic", "Manual", "Disabled", "Unknown"]
    account: str = "Unknown"


@dataclass
class FirewallRule:
    """Windows Firewall rule state."""

    name: str
    display_name: str
    enabled: bool
    direction: Literal["Inbound", "Outbound"]
    protocol: str
    local_port: str | None
    remote_address: str | None
    profile: str  # Domain, Private, Public, Any
    existed_before: bool = True  # False if we created it


@dataclass
class RegistryValue:
    """Registry value state."""

    key: str
    name: str
    value: str | int | None
    value_type: str  # REG_DWORD, REG_SZ, etc.
    existed_before: bool = True


@dataclass
class FullMachineState:
    """Complete machine state for exact restoration."""

    target_id: str
    hostname: str
    captured_at: str  # ISO format
    capture_method: str  # 'auto', 'manual_script'

    # WinRM Configuration
    winrm_service: ServiceState | None = None
    winrm_listeners: list[dict] = field(default_factory=list)
    winrm_config: dict = field(default_factory=dict)

    # Firewall State
    firewall_enabled: dict[str, bool] = field(default_factory=dict)
    firewall_rules: list[FirewallRule] = field(default_factory=list)

    # GPO State
    is_domain_joined: bool = False
    our_gpo_created: bool = False
    our_gpo_name: str | None = None

    # Registry Keys
    registry_snapshot: list[RegistryValue] = field(default_factory=list)

    # TrustedHosts (on client machine)
    trusted_hosts_original: str = ""

    # Related Services
    services: dict[str, ServiceState] = field(default_factory=dict)

    # Rules we created (for easy cleanup)
    rules_we_created: list[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to JSON for storage."""
        return json.dumps(asdict(self), indent=2, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> FullMachineState:
        """Deserialize from JSON."""
        data = json.loads(json_str)

        # Reconstruct nested dataclasses
        if data.get("winrm_service"):
            data["winrm_service"] = ServiceState(**data["winrm_service"])

        if data.get("firewall_rules"):
            data["firewall_rules"] = [FirewallRule(**r) for r in data["firewall_rules"]]

        if data.get("registry_snapshot"):
            data["registry_snapshot"] = [
                RegistryValue(**r) for r in data["registry_snapshot"]
            ]

        if data.get("services"):
            data["services"] = {
                k: ServiceState(**v) for k, v in data["services"].items()
            }

        return cls(**data)


class StateSnapshotCapture:
    """Capture machine state via various methods."""

    # Services we care about
    SERVICES_TO_CAPTURE = [
        "WinRM",
        "RemoteRegistry",
        "Schedule",  # Task Scheduler
        "LanmanServer",  # SMB
        "LanmanWorkstation",
    ]

    # Registry keys to capture
    REGISTRY_KEYS = [
        (
            r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\WSMAN\Client",
            "TrustedHosts",
        ),
        (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Service", "AllowAutoConfig"),
        (r"HKLM\SOFTWARE\Policies\Microsoft\Windows\WinRM\Client", "AllowBasic"),
    ]

    # Firewall rules we might modify
    FIREWALL_RULES = [
        "WINRM-HTTP-In-TCP",
        "WINRM-HTTPS-In-TCP",
        "RemoteEventLogSvc-In-TCP",
        "RemoteEventLogSvc-NP-In-TCP",
    ]

    def __init__(self, target_id: str, hostname: str):
        self.target_id = target_id
        self.hostname = hostname

    def capture_local(self) -> FullMachineState:
        """Capture state of local machine."""
        import subprocess

        state = FullMachineState(
            target_id=self.target_id,
            hostname=self.hostname,
            captured_at=datetime.now(timezone.utc).isoformat(),
            capture_method="auto_local",
        )

        # Capture WinRM service
        state.winrm_service = self._get_service_state("WinRM")

        # Capture TrustedHosts
        state.trusted_hosts_original = self._get_trusted_hosts()

        # Capture firewall state
        state.firewall_enabled = self._get_firewall_profiles()
        state.firewall_rules = self._get_firewall_rules()

        # Capture related services
        for svc in self.SERVICES_TO_CAPTURE:
            svc_state = self._get_service_state(svc)
            if svc_state:
                state.services[svc] = svc_state

        # Check domain status
        state.is_domain_joined = self._is_domain_joined()

        logger.info("Captured local state for %s", self.hostname)
        return state

    def capture_remote_via_wmi(
        self, username: str | None, password: str | None
    ) -> FullMachineState | None:
        """Capture state of remote machine via WMI."""
        import subprocess

        state = FullMachineState(
            target_id=self.target_id,
            hostname=self.hostname,
            captured_at=datetime.now(timezone.utc).isoformat(),
            capture_method="auto_wmi",
        )

        # Build credential args
        cred_args = self._build_wmic_creds(username, password)

        try:
            # Get WinRM service via WMI
            cmd = f'wmic /node:"{self.hostname}" {cred_args} service where name="WinRM" get Name,State,StartMode /format:csv'
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=60
            )
            if result.returncode == 0:
                state.winrm_service = self._parse_wmic_service(result.stdout)

            # Get other services
            for svc in self.SERVICES_TO_CAPTURE:
                cmd = f'wmic /node:"{self.hostname}" {cred_args} service where name="{svc}" get Name,State,StartMode /format:csv'
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=30
                )
                if result.returncode == 0:
                    svc_state = self._parse_wmic_service(result.stdout)
                    if svc_state:
                        state.services[svc] = svc_state

            logger.info("Captured remote state via WMI for %s", self.hostname)
            return state

        except Exception as e:
            logger.warning("WMI state capture failed: %s", e)
            return None

    def _get_service_state(self, name: str) -> ServiceState | None:
        """Get local service state."""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Get-Service {name} | Select-Object Status,StartType | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                return ServiceState(
                    name=name,
                    status=str(data.get("Status", "Unknown")),
                    startup_type=str(data.get("StartType", "Unknown")),
                )
        except Exception as e:
            logger.debug("Cannot get service %s: %s", name, e)
        return None

    def _get_trusted_hosts(self) -> str:
        """Get TrustedHosts value."""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-Item WSMan:\\localhost\\Client\\TrustedHosts -ErrorAction SilentlyContinue).Value",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout.strip() if result.returncode == 0 else ""
        except Exception:
            return ""

    def _get_firewall_profiles(self) -> dict[str, bool]:
        """Get firewall profile states."""
        import subprocess

        profiles = {}
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                if not isinstance(data, list):
                    data = [data]
                for p in data:
                    profiles[p["Name"]] = p["Enabled"]
        except Exception as e:
            logger.debug("Cannot get firewall profiles: %s", e)
        return profiles

    def _get_firewall_rules(self) -> list[FirewallRule]:
        """Get firewall rules we might modify."""
        import subprocess

        rules = []
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "Get-NetFirewallRule -Name 'WINRM*','AutoDBAudit*' -ErrorAction SilentlyContinue | "
                    "Select-Object Name,DisplayName,Enabled,Direction,Profile | ConvertTo-Json",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                if not isinstance(data, list):
                    data = [data]
                for r in data:
                    rules.append(
                        FirewallRule(
                            name=r.get("Name", ""),
                            display_name=r.get("DisplayName", ""),
                            enabled=r.get("Enabled", False),
                            direction=r.get("Direction", "Inbound"),
                            protocol="TCP",
                            local_port="5985",
                            remote_address=None,
                            profile=str(r.get("Profile", "Any")),
                        )
                    )
        except Exception as e:
            logger.debug("Cannot get firewall rules: %s", e)
        return rules

    def _is_domain_joined(self) -> bool:
        """Check if machine is domain-joined."""
        import subprocess

        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "(Get-WmiObject Win32_ComputerSystem).PartOfDomain",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout.strip().lower() == "true"
        except Exception:
            return False

    def _build_wmic_creds(self, username: str | None, password: str | None) -> str:
        """Build WMIC credential arguments."""
        if username and password:
            return f'/user:"{username}" /password:"{password}"'
        return ""

    def _parse_wmic_service(self, output: str) -> ServiceState | None:
        """Parse WMIC service output."""
        lines = [l for l in output.strip().split("\n") if l.strip() and "," in l]
        if len(lines) >= 2:
            parts = lines[1].split(",")
            if len(parts) >= 3:
                return ServiceState(
                    name=parts[0].strip(),
                    status="Running" if "Running" in parts[2] else "Stopped",
                    startup_type=parts[1].strip() if len(parts) > 1 else "Unknown",
                )
        return None


class StateRestorer:
    """Restore machine to captured state."""

    def __init__(self, state: FullMachineState):
        self.state = state

    def restore_local(self) -> list[str]:
        """Restore local machine to captured state. Returns list of actions taken."""
        import subprocess

        actions = []

        # Restore TrustedHosts
        if self.state.trusted_hosts_original is not None:
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value '{self.state.trusted_hosts_original}' -Force",
                    ],
                    timeout=30,
                )
                actions.append(
                    f"Restored TrustedHosts to: {self.state.trusted_hosts_original or '(empty)'}"
                )
            except Exception as e:
                logger.warning("Failed to restore TrustedHosts: %s", e)

        # Remove rules we created
        for rule_name in self.state.rules_we_created:
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Remove-NetFirewallRule -Name '{rule_name}' -ErrorAction SilentlyContinue",
                    ],
                    timeout=15,
                )
                actions.append(f"Removed firewall rule: {rule_name}")
            except Exception as e:
                logger.warning("Failed to remove rule %s: %s", rule_name, e)

        # Restore WinRM service state
        if self.state.winrm_service:
            svc = self.state.winrm_service
            try:
                subprocess.run(
                    [
                        "powershell",
                        "-NoProfile",
                        "-Command",
                        f"Set-Service WinRM -StartupType {svc.startup_type}",
                    ],
                    timeout=30,
                )
                if svc.status == "Stopped":
                    subprocess.run(
                        [
                            "powershell",
                            "-NoProfile",
                            "-Command",
                            "Stop-Service WinRM -Force",
                        ],
                        timeout=30,
                    )
                actions.append(
                    f"Restored WinRM service to: {svc.startup_type}/{svc.status}"
                )
            except Exception as e:
                logger.warning("Failed to restore WinRM: %s", e)

        logger.info("Restored state: %d actions", len(actions))
        return actions
