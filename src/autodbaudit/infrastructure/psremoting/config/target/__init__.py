"""
Target-side WinRM configuration helpers.

The TargetConfigurator delegates to focused helpers for service, firewall,
registry, listeners, and TrustedHosts changes. Each helper returns success
and an optional revert script.
"""

import logging
from typing import Callable, Tuple, Optional

from .service import ensure_winrm_service_running
from .firewall import configure_firewall_rules
from .registry import configure_registry_settings
from .listeners import ensure_winrm_listeners
from .trustedhosts import configure_target_trustedhosts
from .gpupdate import trigger_gpupdate

logger = logging.getLogger(__name__)


class TargetConfigurator:
    """Apply WinRM-related settings on a target host."""

    def ensure_winrm_service_running(self, server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
        return ensure_winrm_service_running(server_name, runner)

    def configure_firewall_rules(self, server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
        return configure_firewall_rules(server_name, runner)

    def configure_registry_settings(self, server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
        return configure_registry_settings(server_name, runner)

    def ensure_winrm_listeners(self, server_name: str, runner: Callable[[str], object]) -> Tuple[bool, Optional[str]]:
        return ensure_winrm_listeners(server_name, runner)

    def configure_target_trustedhosts(
        self, server_name: str, client_ip: str, runner: Callable[[str], object]
    ) -> Tuple[bool, Optional[str]]:
        return configure_target_trustedhosts(server_name, client_ip, runner)

    def trigger_gpupdate(self, server_name: str, runner: Callable[[str], object]) -> bool:
        return trigger_gpupdate(server_name, runner)
