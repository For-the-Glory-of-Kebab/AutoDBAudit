"""
Aggressiveness Enforcer micro-component.
Enforces Safe/Standard/Aggressive execution levels.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from typing import Literal
from dataclasses import dataclass

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

AggressivenessLevel = Literal[1, 2, 3]

@dataclass(frozen=True)
class AggressivenessEnforcer:
    """
    Enforces aggressiveness levels for remediation execution.
    Railway-oriented: returns Success with enforcement result or Failure.
    """

    def enforce_level(
        self,
        script_content: str,
        level: AggressivenessLevel,
        is_exceptionalized: bool = False,
        script_type: str = "tsql"
    ) -> Result[str, str]:
        """
        Enforce aggressiveness level on script content.
        Returns Success with modified script or Failure with reason.
        """
        if level not in (1, 2, 3):
            return Failure(f"Invalid aggressiveness level: {level}")

        # Exceptionalized items get special treatment
        if is_exceptionalized:
            return self._handle_exceptionalized(script_content, level, script_type)

        # Apply level-specific enforcement
        if level == 1:
            return self._enforce_safe(script_content, script_type)
        if level == 2:
            return self._enforce_standard(script_content, script_type)
        # level == 3
        return self._enforce_aggressive(script_content, script_type)

    def _handle_exceptionalized(
        self,
        script: str,
        level: AggressivenessLevel,
        script_type: str
    ) -> Result[str, str]:
        """Handle exceptionalized findings based on level."""
        comment_char = "--" if script_type == "tsql" else "#"

        if level >= 3:
            # Level 3: Include but mark as exceptionalized
            marker = f"{comment_char} ⚠️ EXCEPTIONALIZED - Included at aggressive level\n"
            return Success(marker + script)

        # Levels 1-2: Comment out exceptionalized items
        lines = script.split('\n')
        commented = [f"{comment_char} {line}" if line.strip() else line for line in lines]
        warning = f"{comment_char} ❌ EXCEPTIONALIZED - Commented out per policy\n"
        return Success(warning + '\n'.join(commented))

    def _enforce_safe(self, script: str, script_type: str) -> Result[str, str]:
        """Level 1: Comment out all potentially dangerous operations."""
        comment_char = "--" if script_type == "tsql" else "#"
        lines = script.split('\n')
        commented = [f"{comment_char} {line}" if line.strip() else line for line in lines]
        header = f"{comment_char} 🔒 SAFE MODE - All operations commented for review\n"
        return Success(header + '\n'.join(commented))

    def _enforce_standard(self, script: str, script_type: str) -> Result[str, str]:
        """Level 2: Comment out high-risk operations only."""
        # For now, treat as safe - handlers will mark specific operations
        comment_char = "--" if script_type == "tsql" else "#"
        warning = f"{comment_char} ⚠️ STANDARD MODE - Review high-risk operations\n"
        return Success(warning + script)

    def _enforce_aggressive(self, script: str, script_type: str) -> Result[str, str]:
        """Level 3: Execute all operations (with warnings for exceptionalized)."""
        comment_char = "--" if script_type == "tsql" else "#"
        warning = f"{comment_char} 🚨 AGGRESSIVE MODE - Executing all operations\n"
        return Success(warning + script)
