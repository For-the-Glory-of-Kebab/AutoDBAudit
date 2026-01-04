"""
Layer 3 target-side configuration runner for PS remoting.
"""

import logging
from typing import List, Callable

from .models import ConnectionAttempt, PSRemotingResult, CredentialBundle
from .direct_runner import DirectAttemptRunner
from .target_config import TargetConfigurator
from .revert_tracker import RevertTracker
from .gpo_enforcer import apply_winrm_policy, build_revert_script

logger = logging.getLogger(__name__)
# pylint: disable=line-too-long,too-many-arguments,too-many-positional-arguments


class TargetLayerRunner:
    """Handles WinRM enablement on the target before retrying direct attempts."""

    def __init__(
        self,
        target_config: TargetConfigurator,
        revert_tracker: RevertTracker,
        direct_runner: DirectAttemptRunner,
        is_ip_address: Callable[[str], bool],
        has_admin_credentials: Callable[[CredentialBundle], bool],
        exec_with_creds: Callable[[str, CredentialBundle], object],
    ):
        self.target_config = target_config
        self.revert_tracker = revert_tracker
        self.direct_runner = direct_runner
        self._is_ip_address = is_ip_address
        self._has_admin_credentials = has_admin_credentials
        self._exec_with_creds = exec_with_creds

    def run(
        self,
        server_name: str,
        bundle: CredentialBundle,
        attempts: List[ConnectionAttempt],
        profile_id: int,
    ) -> PSRemotingResult:
        """Apply target-side configuration then retry direct connections."""
        if not self._has_admin_credentials(bundle):
            return PSRemotingResult(
                success=False,
                session=None,
                error_message="Layer 3: Admin credentials required for target configuration",
                attempts_made=attempts,
                duration_ms=0,
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=None,
            )

        try:
            self._ensure_winrm_service_running(server_name, bundle)
            self._configure_firewall_rules(server_name, bundle)
            self._configure_registry_settings(server_name, bundle)
            self._configure_gpo_settings(server_name, bundle)
            self._ensure_winrm_listeners(server_name, bundle)
            self._configure_target_trustedhosts(server_name, bundle)

            return self.direct_runner.layer1_direct_attempts(
                server_name, bundle, attempts, profile_id
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Layer 3: Target configuration failed for %s: %s", server_name, exc)
            return PSRemotingResult(
                success=False,
                session=None,
                error_message=f"Layer 3: Target configuration failed: {exc}",
                attempts_made=attempts,
                duration_ms=0,
                troubleshooting_report=None,
                manual_setup_scripts=None,
                revert_scripts=None,
            )

    def _ensure_winrm_service_running(self, server_name: str, bundle: CredentialBundle) -> None:
        success, revert = self.target_config.ensure_winrm_service_running(
            server_name, lambda script: self._exec_with_creds(script, bundle)
        )
        if success:
            self.revert_tracker.track_change("winrm_service", server_name, "started_automatic")
            if revert:
                self.revert_tracker.add_revert_script(revert)

    def _configure_firewall_rules(self, server_name: str, bundle: CredentialBundle) -> None:
        success, revert = self.target_config.configure_firewall_rules(
            server_name, lambda script: self._exec_with_creds(script, bundle)
        )
        if success:
            self.revert_tracker.track_change("firewall_rules", server_name, "winrm_enabled")
            if revert:
                self.revert_tracker.add_revert_script(revert)

    def _configure_registry_settings(self, server_name: str, bundle: CredentialBundle) -> None:
        success, revert = self.target_config.configure_registry_settings(
            server_name, lambda script: self._exec_with_creds(script, bundle)
        )
        if success:
            self.revert_tracker.track_change("registry_settings", server_name, "remoting_enabled")
            if revert:
                self.revert_tracker.add_revert_script(revert)

    def _configure_gpo_settings(self, server_name: str, bundle: CredentialBundle) -> None:
        """Enable WinRM auth/unencrypted policy and track revert."""
        success, previous = apply_winrm_policy(
            server_name, lambda script: self._exec_with_creds(script, bundle)
        )
        if success:
            self.revert_tracker.track_change("gpo_policy", server_name, "winrm_auth_enabled")
            self.revert_tracker.add_revert_script(build_revert_script(server_name, previous))

    def _ensure_winrm_listeners(self, server_name: str, bundle: CredentialBundle) -> None:
        success, revert = self.target_config.ensure_winrm_listeners(
            server_name, lambda script: self._exec_with_creds(script, bundle)
        )
        if success:
            self.revert_tracker.track_change("winrm_listeners", server_name, "verified")
            if revert:
                self.revert_tracker.add_revert_script(revert)

    def _configure_target_trustedhosts(self, server_name: str, bundle: CredentialBundle) -> None:
        if not self._is_ip_address(server_name):
            return

        client_ip = self._get_client_ip()
        success, revert = self.target_config.configure_target_trustedhosts(
            server_name, client_ip, lambda script: self._exec_with_creds(script, bundle)
        )
        if success:
            self.revert_tracker.track_change("target_trustedhosts", server_name, f"added_{client_ip}")
            if revert:
                self.revert_tracker.add_revert_script(revert)

    def _get_client_ip(self) -> str:
        """Obtain client IP using the client configurator helper."""
        from .client_config import ClientConfigurator  # pylint: disable=import-outside-toplevel

        return ClientConfigurator().detect_client_ip()
