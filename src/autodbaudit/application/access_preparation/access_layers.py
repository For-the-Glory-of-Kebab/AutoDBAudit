"""
Access Layers - Multi-method remote access enablement.

Implements 8 fallback layers for enabling PSRemoting on restricted environments:
1. WinRM (existing)
2. WMI
3. PsExec
4. schtasks
5. SC.exe
6. reg.exe
7. PowerShell Direct (Hyper-V)
8. Manual Script Generation
"""

from __future__ import annotations

import logging
import subprocess
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.infrastructure.config_loader import SqlTarget

logger = logging.getLogger(__name__)


@dataclass
class LayerResult:
    """Result from an access layer attempt."""

    layer: str
    success: bool
    error_type: str | None = None  # 'auth', 'network', 'permission', 'gpo', 'timeout'
    error_message: str | None = None
    remediation_hint: str | None = None
    changes_made: list[dict] | None = None


class AccessLayer(ABC):
    """Base class for access layers."""

    name: str
    timeout: int  # seconds

    def __init__(self, hostname: str, username: str | None, password: str | None):
        self.hostname = hostname
        self.username = username
        self.password = password

    @abstractmethod
    def test_access(self) -> bool:
        """Test if this layer can reach the target."""
        pass

    @abstractmethod
    def enable_winrm(self) -> LayerResult:
        """Enable WinRM using this layer's method."""
        pass

    def _run_cmd(
        self, cmd: str | list, timeout: int | None = None
    ) -> tuple[int, str, str]:
        """Run command and return (returncode, stdout, stderr)."""
        try:
            if isinstance(cmd, str):
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=timeout or self.timeout,
                )
            else:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=timeout or self.timeout
                )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Timeout"
        except Exception as e:
            return -1, "", str(e)

    def _classify_error(self, error: str) -> tuple[str, str]:
        """Classify error and provide remediation hint."""
        error_lower = error.lower()

        if "access is denied" in error_lower or "access denied" in error_lower:
            return "auth", "Verify credentials have local admin rights on target"

        if "network path" in error_lower or "not found" in error_lower:
            return "network", "Check network connectivity and DNS resolution"

        if "rpc server" in error_lower or "unavailable" in error_lower:
            return "network", "Target may be offline or RPC blocked"

        if "gpo" in error_lower or "policy" in error_lower:
            return "gpo", "Group Policy may be blocking changes"

        if "timeout" in error_lower:
            return "timeout", "Increase timeout or check network latency"

        if "firewall" in error_lower:
            return "firewall", "Firewall may be blocking required ports"

        return "unknown", "Check logs for details"


class Layer0_LocalDirect(AccessLayer):
    """Layer 0: Direct local execution (bypasses network)."""

    name = "LocalDirect"
    timeout = 60

    def _is_local(self) -> bool:
        """Check if target is current machine."""
        import platform
        import socket

        normalized = self.hostname.lower()
        if normalized in ("localhost", "127.0.0.1", ".", "::1"):
            return True

        try:
            return (
                normalized == platform.node().lower()
                or normalized == socket.gethostname().lower()
            )
        except Exception:
            return False

    def test_access(self) -> bool:
        """Always accessible if local."""
        return self._is_local()

    def enable_winrm(self) -> LayerResult:
        """
        Enable WinRM using an aggressive, multi-layered local approach.

        Actions:
        1. Enable-PSRemoting
        2. Set WinRM service to Auto and Start it
        3. Configure TrustedHosts to * (crucial for localhost creds)
        4. Open Firewall Port 5985
        5. Set Registry keys (DisableLoopbackCheck, LocalAccountTokenFilterPolicy)
        6. VERIFY access by actually creating a session
        """
        if not self._is_local():
            return LayerResult(
                layer=self.name,
                success=False,
                error_type="not_applicable",
                error_message="Target is not local machine",
            )

        # 1. Aggressive Enablement Script
        # We use a single large block to minimize subprocess overhead and context switching
        cmd = (
            'powershell -NoProfile -ExecutionPolicy Bypass -Command "'
            # A. Basic Enable
            "Enable-PSRemoting -Force -SkipNetworkProfileCheck; "
            # B. Service Enforcement
            "Set-Service WinRM -StartupType Automatic; "
            "Start-Service WinRM; "
            # C. Registry: Allow Loopback (Required for using credentials against localhost)
            "New-ItemProperty -Path HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa -Name DisableLoopbackCheck -Value 1 -PropertyType DWord -Force; "
            # D. Registry: Local Account Token Filter (Allows admin shares with local accounts)
            "New-ItemProperty -Path HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System -Name LocalAccountTokenFilterPolicy -Value 1 -PropertyType DWord -Force; "
            # E. Trusted Hosts (Bypass auth restrictions for localhost)
            "Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value * -Force; "
            "Restart-Service WinRM; "
            # F. Firewall (Ensure port 5985 is open)
            "New-NetFirewallRule -Name 'AutoDBAudit_WinRM' -DisplayName 'AutoDBAudit WinRM' -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 5985 -ErrorAction SilentlyContinue; "
            '"'
        )

        code, stdout, stderr = self._run_cmd(cmd)

        if code != 0:
            # Check for elevation error
            if (
                "run as administrator" in stdout.lower()
                or "run as administrator" in stderr.lower()
                or "access is denied" in stderr.lower()
            ):
                return LayerResult(
                    layer=self.name,
                    success=False,
                    error_type="auth",
                    error_message=f"Access Denied during setup. Run As Admin required.\nDetails: {stderr}",
                    remediation_hint="Right-click -> Run as Administrator",
                )

            error_type, hint = self._classify_error(stderr or stdout)
            return LayerResult(
                layer=self.name,
                success=False,
                error_type=error_type,
                error_message=f"Setup failed: {stderr or stdout}",
                remediation_hint=hint,
            )

        # 2. Strict Verification
        # We successfully ran the setup commands, but we must PROVE it works.
        # Try to actually create a session to localhost.
        verify_cmd = (
            'powershell -NoProfile -ExecutionPolicy Bypass -Command "'
            "$s = New-PSSession -ComputerName localhost; "
            "if ($s) { Remove-PSSession $s; exit 0 } else { exit 1 }"
            '"'
        )

        v_code, v_stdout, v_stderr = self._run_cmd(verify_cmd)

        if v_code == 0:
            return LayerResult(
                layer=self.name,
                success=True,
                changes_made=[{"action": "local_direct_enable_verified"}],
            )
        else:
            # Setup seemed to work, but connection still fails
            return LayerResult(
                layer=self.name,
                success=False,
                error_type="verification_failed",
                error_message=f"Setup commands ran, but verification connection failed.\nVerify Error: {v_stderr} {v_stdout}",
                remediation_hint="Check if port 5985 is blocked by 3rd party antivirus or firewall.",
            )


class Layer1_WinRM(AccessLayer):
    """Layer 1: Test existing WinRM access."""

    name = "WinRM"
    timeout = 60

    def test_access(self) -> bool:
        """Test if WinRM works by establishing a real session."""
        # Test-WSMan is insufficient (only checks port/service).
        # We must verify a session can be created (auth + configuration).
        creds = ""
        if self.username and self.password:
            creds = f"-Credential (New-Object System.Management.Automation.PSCredential ('{self.username}', (ConvertTo-SecureString '{self.password}' -AsPlainText -Force)))"

        cmd = (
            'powershell -NoProfile -ExecutionPolicy Bypass -Command "'
            f"$s = New-PSSession -ComputerName {self.hostname} {creds} -ErrorAction Stop; "
            "if ($s) { Remove-PSSession $s; exit 0 } else { exit 1 }"
            '"'
        )
        code, stdout, stderr = self._run_cmd(cmd)
        return code == 0

    def enable_winrm(self) -> LayerResult:
        """WinRM already tested - this layer only tests, doesn't enable."""
        if self.test_access():
            return LayerResult(layer=self.name, success=True)
        return LayerResult(
            layer=self.name,
            success=False,
            error_type="not_available",
            error_message="WinRM not yet configured on target",
        )


class Layer2_WMI(AccessLayer):
    """Layer 2: Enable WinRM via WMI (RPC-based)."""

    name = "WMI"
    timeout = 90

    def _build_creds(self) -> str:
        if self.username and self.password:
            return f'/user:"{self.username}" /password:"{self.password}"'
        return ""

    def test_access(self) -> bool:
        """Test if WMI works."""
        creds = self._build_creds()
        cmd = f'wmic /node:"{self.hostname}" {creds} os get caption /format:value'
        code, stdout, stderr = self._run_cmd(cmd, timeout=30)
        return code == 0 and "Caption" in stdout

    def enable_winrm(self) -> LayerResult:
        """Enable WinRM via WMI process creation."""
        if not self.test_access():
            return LayerResult(
                layer=self.name,
                success=False,
                error_type="network",
                error_message="WMI access not available",
            )

        creds = self._build_creds()

        # Start WinRM service
        cmd = f'wmic /node:"{self.hostname}" {creds} service where name="WinRM" call StartService'
        code, stdout, stderr = self._run_cmd(cmd)

        if code != 0:
            error_type, hint = self._classify_error(stderr)
            return LayerResult(
                layer=self.name,
                success=False,
                error_type=error_type,
                error_message=stderr,
                remediation_hint=hint,
            )

        # Set to auto-start
        cmd = f'wmic /node:"{self.hostname}" {creds} service where name="WinRM" call ChangeStartMode StartMode="Automatic"'
        self._run_cmd(cmd)

        # Run Enable-PSRemoting via process create (more robust than winrm quickconfig)
        # Also set LocalAccountTokenFilterPolicy for local admin access
        cmd = (
            f'wmic /node:"{self.hostname}" {creds} process call create '
            f'"powershell -NoProfile -Command \\"Enable-PSRemoting -Force -SkipNetworkProfileCheck; '
            f"New-ItemProperty -Path HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System -Name LocalAccountTokenFilterPolicy -Value 1 -PropertyType DWord -Force; "
            f'New-ItemProperty -Path HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa -Name DisableLoopbackCheck -Value 1 -PropertyType DWord -Force\\""'
        )
        code, stdout, stderr = self._run_cmd(cmd)

        return LayerResult(
            layer=self.name,
            success=code == 0,
            error_message=stderr if code != 0 else None,
            changes_made=[{"action": "wmi_winrm_enable"}],
        )


class Layer3_PsExec(AccessLayer):
    """Layer 3: Enable WinRM via PsExec (SMB-based)."""

    name = "PsExec"
    timeout = 120

    def _get_psexec_path(self) -> Path | None:
        """Find PsExec executable."""
        # Check bundled location
        bundled = (
            Path(__file__).parent.parent.parent.parent.parent / "assets" / "PsExec.exe"
        )
        if bundled.exists():
            return bundled

        # Check PATH
        if shutil.which("PsExec"):
            return Path(shutil.which("PsExec"))
        if shutil.which("psexec"):
            return Path(shutil.which("psexec"))

        return None

    def test_access(self) -> bool:
        """Test if SMB admin share accessible."""
        cmd = f"net use \\\\{self.hostname}\\admin$ /delete /y 2>nul & net use \\\\{self.hostname}\\admin$"
        if self.username and self.password:
            cmd += f" /user:{self.username} {self.password}"
        code, stdout, stderr = self._run_cmd(cmd, timeout=30)
        # Clean up
        subprocess.run(
            f"net use \\\\{self.hostname}\\admin$ /delete /y",
            shell=True,
            capture_output=True,
        )
        return code == 0

    def enable_winrm(self) -> LayerResult:
        """Enable WinRM via PsExec."""
        psexec = self._get_psexec_path()
        if not psexec:
            return LayerResult(
                layer=self.name,
                success=False,
                error_type="missing_tool",
                error_message="PsExec not found",
                remediation_hint="Bundle PsExec.exe in assets/ folder",
            )

        creds = ""
        if self.username and self.password:
            creds = f"-u {self.username} -p {self.password}"

        # Enable WinRM via PsExec

        # Includes Enable-PSRemoting, LocalAccountTokenFilterPolicy, and DisableLoopbackCheck
        cmd = (
            f'"{psexec}" \\\\{self.hostname} {creds} -accepteula -s powershell -NoProfile -Command "'
            f"Enable-PSRemoting -Force -SkipNetworkProfileCheck; "
            f"New-ItemProperty -Path HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System -Name LocalAccountTokenFilterPolicy -Value 1 -PropertyType DWord -Force; "
            f"New-ItemProperty -Path HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Lsa -Name DisableLoopbackCheck -Value 1 -PropertyType DWord -Force"
            f'"'
        )
        code, stdout, stderr = self._run_cmd(cmd)

        if code != 0:
            error_type, hint = self._classify_error(stderr)
            return LayerResult(
                layer=self.name,
                success=False,
                error_type=error_type,
                error_message=stderr,
                remediation_hint=hint,
            )

        return LayerResult(
            layer=self.name,
            success=True,
            changes_made=[{"action": "psexec_winrm_enable"}],
        )


class Layer4_ScheduledTask(AccessLayer):
    """Layer 4: Enable WinRM via scheduled task (SMB-based)."""

    name = "schtasks"
    timeout = 120

    def test_access(self) -> bool:
        """Test if schtasks can reach target."""
        cmd = f"schtasks /query /s {self.hostname} /fo csv"
        if self.username and self.password:
            cmd += f" /u {self.username} /p {self.password}"
        code, stdout, stderr = self._run_cmd(cmd, timeout=30)
        return code == 0

    def enable_winrm(self) -> LayerResult:
        """Enable WinRM via scheduled task."""
        task_name = "AutoDBAudit_EnableWinRM"
        creds = ""
        if self.username and self.password:
            creds = f"/u {self.username} /p {self.password}"

        # Create task
        cmd = (
            f"schtasks /create /s {self.hostname} {creds} "
            f'/tn "{task_name}" /tr "cmd /c winrm quickconfig -quiet" '
            f"/sc once /st 00:00 /ru SYSTEM /f"
        )
        code, stdout, stderr = self._run_cmd(cmd)

        if code != 0:
            error_type, hint = self._classify_error(stderr)
            return LayerResult(
                layer=self.name,
                success=False,
                error_type=error_type,
                error_message=stderr,
                remediation_hint=hint,
            )

        # Run task immediately
        cmd = f'schtasks /run /s {self.hostname} {creds} /tn "{task_name}"'
        code, stdout, stderr = self._run_cmd(cmd)

        # Wait for task to complete
        import time

        time.sleep(5)

        # Delete task
        cmd = f'schtasks /delete /s {self.hostname} {creds} /tn "{task_name}" /f'
        self._run_cmd(cmd)

        return LayerResult(
            layer=self.name,
            success=True,
            changes_made=[{"action": "schtasks_winrm_enable"}],
        )


class Layer5_ServiceControl(AccessLayer):
    """Layer 5: Enable WinRM via SC.exe (Service Control Manager)."""

    name = "SC.exe"
    timeout = 60

    def test_access(self) -> bool:
        """Test if SC can reach target."""
        cmd = f"sc \\\\{self.hostname} query WinRM"
        code, stdout, stderr = self._run_cmd(cmd, timeout=20)
        return code == 0

    def enable_winrm(self) -> LayerResult:
        """Start WinRM service via SC.exe."""
        # Set to auto-start
        cmd = f"sc \\\\{self.hostname} config WinRM start= auto"
        code, stdout, stderr = self._run_cmd(cmd)

        if code != 0:
            error_type, hint = self._classify_error(stderr)
            return LayerResult(
                layer=self.name,
                success=False,
                error_type=error_type,
                error_message=stderr,
                remediation_hint=hint,
            )

        # Start service
        cmd = f"sc \\\\{self.hostname} start WinRM"
        code, stdout, stderr = self._run_cmd(cmd)

        # SC returns 0 even if service already running
        return LayerResult(
            layer=self.name, success=True, changes_made=[{"action": "sc_winrm_start"}]
        )


class Layer6_RemoteRegistry(AccessLayer):
    """Layer 6: Configure WinRM via remote registry."""

    name = "RemoteRegistry"
    timeout = 60

    def test_access(self) -> bool:
        """Test if remote registry accessible."""
        cmd = f"reg query \\\\{self.hostname}\\HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion /v ProgramFilesDir"
        code, stdout, stderr = self._run_cmd(cmd, timeout=20)
        return code == 0

    def enable_winrm(self) -> LayerResult:
        """Configure WinRM via registry."""
        # This only configures, doesn't start service
        # Set AllowAutoConfig
        cmd = (
            f"reg add \\\\{self.hostname}\\HKLM\\SOFTWARE\\Policies\\Microsoft\\Windows\\WinRM\\Service "
            f"/v AllowAutoConfig /t REG_DWORD /d 1 /f"
        )
        code, stdout, stderr = self._run_cmd(cmd)

        if code != 0:
            error_type, hint = self._classify_error(stderr)
            return LayerResult(
                layer=self.name,
                success=False,
                error_type=error_type,
                error_message=stderr,
                remediation_hint=hint,
            )

        return LayerResult(
            layer=self.name,
            success=True,
            changes_made=[
                {"action": "registry_winrm_config", "key": "AllowAutoConfig"}
            ],
        )


class Layer7_PowerShellDirect(AccessLayer):
    """Layer 7: PowerShell Direct (Hyper-V VMs only)."""

    name = "PSDirectHyperV"
    timeout = 60

    def test_access(self) -> bool:
        """Test if target is a Hyper-V VM we can access."""
        # This only works if target is a VM on a Hyper-V host we can access
        cmd = f'powershell -NoProfile -Command "Get-VM -Name {self.hostname} -ErrorAction Stop"'
        code, stdout, stderr = self._run_cmd(cmd, timeout=20)
        return code == 0

    def enable_winrm(self) -> LayerResult:
        """Enable WinRM via PowerShell Direct."""
        if not self.test_access():
            return LayerResult(
                layer=self.name,
                success=False,
                error_type="not_applicable",
                error_message="Target is not a Hyper-V VM on this host",
            )

        cmd = (
            f'powershell -NoProfile -Command "'
            f"Invoke-Command -VMName {self.hostname} -ScriptBlock {{ Enable-PSRemoting -Force }}"
            f'"'
        )
        code, stdout, stderr = self._run_cmd(cmd)

        return LayerResult(
            layer=self.name,
            success=code == 0,
            error_message=stderr if code != 0 else None,
            changes_made=[{"action": "psdirect_winrm_enable"}] if code == 0 else None,
        )


class AccessLayerOrchestrator:
    """Orchestrate all access layers with fallback."""

    def __init__(
        self, hostname: str, username: str | None = None, password: str | None = None
    ):
        self.hostname = hostname
        self.username = username
        self.password = password

        # Initialize layers in order
        self.layers: list[AccessLayer] = [
            Layer0_LocalDirect(hostname, username, password),
            Layer1_WinRM(hostname, username, password),
            Layer2_WMI(hostname, username, password),
            Layer3_PsExec(hostname, username, password),
            Layer4_ScheduledTask(hostname, username, password),
            Layer5_ServiceControl(hostname, username, password),
            Layer6_RemoteRegistry(hostname, username, password),
            Layer7_PowerShellDirect(hostname, username, password),
        ]

    def try_all_layers(self) -> tuple[bool, list[LayerResult]]:
        """
        Try all layers in sequence until one succeeds.

        Returns:
            (success, list of all layer results)
        """
        results = []

        for layer in self.layers:
            logger.info("Trying layer: %s for %s", layer.name, self.hostname)

            try:
                result = layer.enable_winrm()
                results.append(result)

                if result.success:
                    # Verify WinRM now works
                    if Layer1_WinRM(
                        self.hostname, self.username, self.password
                    ).test_access():
                        logger.info(
                            "Layer %s succeeded for %s", layer.name, self.hostname
                        )
                        return True, results
                    else:
                        logger.warning(
                            "Layer %s completed but WinRM still not accessible",
                            layer.name,
                        )
                else:
                    logger.debug(
                        "Layer %s failed: %s", layer.name, result.error_message
                    )

            except Exception as e:
                logger.warning("Layer %s exception: %s", layer.name, e)
                results.append(
                    LayerResult(
                        layer=layer.name,
                        success=False,
                        error_type="exception",
                        error_message=str(e),
                    )
                )

        return False, results

    def test_current_access(self) -> str | None:
        """Test which access methods currently work. Returns first working layer name."""
        for layer in self.layers:
            if layer.test_access():
                return layer.name
        return None
