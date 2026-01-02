"""
Target Parser micro-component.
Parses target identifiers into hostname and instance components.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    pass

@dataclass(frozen=True)
class ParsedTarget:
    """Parsed target information."""
    hostname: str
    instance_name: str

@dataclass(frozen=True)
class TargetParser:
    """
    Parses target identifiers into components.
    Railway-oriented: returns Success with parsed target or Failure.
    """

    def parse_target_id(self, target_id: str) -> Result[ParsedTarget, str]:
        """
        Parse target ID into hostname and instance name.
        Supports formats: "hostname|instance" or "hostname\\instance"

        Returns Success with ParsedTarget or Failure on invalid format.
        """
        if not target_id or not target_id.strip():
            return Failure("Empty or invalid target ID")

        target_id = target_id.strip()

        # Format 1: "hostname|instance"
        if "|" in target_id:
            parts = target_id.split("|", 1)
            if len(parts) != 2 or not all(parts):
                return Failure(f"Invalid target format: {target_id}")
            hostname, instance_name = parts

        # Format 2: "hostname\\instance"
        elif "\\" in target_id:
            parts = target_id.split("\\", 1)
            if len(parts) != 2 or not all(parts):
                return Failure(f"Invalid target format: {target_id}")
            hostname, instance_name = parts

        # Format 3: hostname only (default instance)
        else:
            hostname = target_id
            instance_name = "MSSQLSERVER"

        # Validate components
        if not hostname:
            return Failure("Hostname cannot be empty")

        if not instance_name:
            instance_name = "MSSQLSERVER"

        parsed = ParsedTarget(
            hostname=hostname.strip(),
            instance_name=instance_name.strip()
        )

        return Success(parsed)
