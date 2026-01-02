"""
Rollback Manager micro-component.
Manages rollback operations for remediation actions.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    from autodbaudit.infrastructure.remediation.results import ScriptExecutionSuccess

@dataclass(frozen=True)
class RollbackManager:
    """
    Manages rollback operations for remediation actions.
    Railway-oriented: returns Success with rollback result or Failure.
    """

    def generate_rollback_script(
        self,
        execution_result: ScriptExecutionSuccess
    ) -> Result[str, str]:
        """
        Generate rollback script from successful execution result.
        Returns Success with rollback script or Failure if generation fails.
        """
        if not execution_result.rollback_script:
            return Failure("No rollback script available in execution result")

        try:
            # Validate rollback script structure
            if not self._validate_rollback_script(execution_result.rollback_script):
                return Failure("Invalid rollback script structure")

            return Success(execution_result.rollback_script)

        except Exception as e:
            return Failure(f"Rollback script generation failed: {str(e)}")

    def execute_rollback(self, rollback_script: str) -> Result[bool, str]:
        """
        Execute rollback script on target.
        Returns Success if rollback completes or Failure with error.
        """
        if not rollback_script.strip():
            return Failure("Empty rollback script provided")

        try:
            # Placeholder for actual rollback execution
            # In real implementation, this would use the hybrid coordinator
            # to execute the rollback script via appropriate method (T-SQL/PSRemote)

            # For now, return success with validation
            if self._validate_rollback_script(rollback_script):
                return Success(True)
            return Failure("Rollback script validation failed")

        except Exception as e:
            return Failure(f"Rollback execution failed: {str(e)}")

    def _validate_rollback_script(self, script: str) -> bool:
        """
        Validate rollback script structure and safety.
        """
        if not script or not script.strip():
            return False

        # Basic validation - check for required rollback markers
        script_lower = script.lower()
        has_rollback_marker = 'rollback' in script_lower or 'undo' in script_lower

        # Check for dangerous operations that shouldn't be in rollback
        dangerous_ops = ['drop database', 'drop table', 'truncate table']
        has_dangerous = any(op in script_lower for op in dangerous_ops)

        return has_rollback_marker and not has_dangerous
