"""
Base classes and context for remediation handlers.
"""

from __future__ import annotations

import string
import secrets
from abc import ABC
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass
class RemediationAction:
    """Represents a single remediation action."""

    script: str
    rollback: str
    category: str = "SAFE"  # SAFE, CAUTION, REVIEW, INFO


@dataclass
class RemediationContext:
    """Shared context for remediation generation."""

    server_name: str
    instance_name: str
    inst_id: int
    port: int
    conn_user: str | None
    aggressiveness: int

    # Mutable state for collecting secrets
    secrets_log: list[str] = field(default_factory=list)

    @property
    def instance_label(self) -> str:
        if self.instance_name:
            return self.instance_name
        elif self.port and self.port != 1433:
            return f"(Default:{self.port})"
        return "(Default)"


class RemediationHandler(ABC):
    """
    Abstract Base Class for remediation handlers.
    """

    def __init__(self, context: RemediationContext) -> None:
        self.ctx = context

    def generate_temp_password(self) -> str:
        """Generate a secure temporary password (16 chars)."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(16))

    def _category_header(self, tag: str, description: str) -> str:
        """Generate a category header with searchable tag."""
        return f"""
-- ╔══════════════════════════════════════════════════════════════════════════╗
-- ║ [{tag}] {description}
-- ╚══════════════════════════════════════════════════════════════════════════╝
"""

    def _item_header(self, tag: str, title: str) -> str:
        """Generate a standardized header for an individual remediation item."""
        return f"""
-- ============================================================================
-- [{tag}] {title}
-- ============================================================================"""

    def handle(self, finding: dict) -> list[RemediationAction]:
        """
        Process a single finding and return immediate actions.
        Override this to either return actions immediately or buffer them.
        """
        raise NotImplementedError

    def finalize(self) -> list[RemediationAction]:
        """
        Return any buffered actions after all findings have been processed.
        Override this if the handler buffers findings for batched processing.
        """
        return []

    def _wrap_lockout_warning(self, script: str, username: str) -> str:
        """Wrap a script in comments with a lockout warning."""
        lines = script.split("\n")
        commented_lines = [f"-- {line}" if line.strip() else line for line in lines]
        warning = f"""
/* 
!!! LOCKOUT RISK: YOU ARE CONNECTED AS '{username}' !!!
=========================================================
This section has been commented out because we detected
that you used the '{username}' account to connect to this Audit.

altering this login could cause you to lose access immediately!
Run this only if you have another SysAdmin account ready!
*/
"""
        return warning + "\n".join(commented_lines)
