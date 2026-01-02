"""
Dry Run Validator micro-component.
Validates remediation actions in simulation mode.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    from autodbaudit.infrastructure.remediation.results import ScriptExecutionSuccess

@dataclass(frozen=True)
class DryRunValidator:
    """
    Validates remediation actions in dry-run/simulation mode.
    Railway-oriented: returns Success with validation result or Failure.
    """

    def validate_dry_run(
        self,
        script: str,
        script_type: str
    ) -> Result[dict, str]:
        """
        Validate script for dry-run execution.
        Returns Success with validation details or Failure with issues.
        """
        if not script or not script.strip():
            return Failure("Empty script provided for validation")

        try:
            validation_result = {
                'is_valid': True,
                'warnings': [],
                'estimated_impact': 'low',
                'requires_confirmation': False
            }

            # Parse and analyze script
            analysis = self._analyze_script(script, script_type)

            # Check for high-impact operations
            if analysis['has_destructive_ops']:
                validation_result['estimated_impact'] = 'high'
                validation_result['requires_confirmation'] = True
                validation_result['warnings'].append("Script contains destructive operations")

            # Check for untested patterns
            if analysis['has_untested_patterns']:
                validation_result['warnings'].append("Script contains untested patterns")
                validation_result['requires_confirmation'] = True

            # Validate syntax
            if not analysis['syntax_valid']:
                validation_result['is_valid'] = False
                return Failure("Script syntax validation failed")

            return Success(validation_result)

        except Exception as e:
            return Failure(f"Dry-run validation failed: {str(e)}")

    def generate_preview(
        self,
        validation_result: dict,
        script: str
    ) -> Result[str, str]:
        """
        Generate human-readable preview of what the script would do.
        Returns Success with preview text or Failure.
        """
        try:
            preview_lines = [
                "DRY RUN PREVIEW",
                "=" * 50,
                f"Target: {validation_result.get('target', 'unknown')}",
                f"Impact Level: {validation_result.get('estimated_impact', 'unknown')}",
                "",
                "Script Analysis:",
            ]

            if validation_result.get('warnings'):
                preview_lines.append("⚠️  Warnings:")
                for warning in validation_result['warnings']:
                    preview_lines.append(f"   - {warning}")

            preview_lines.extend([
                "",
                "Script Preview:",
                "-" * 20,
                script[:200] + "..." if len(script) > 200 else script,
                "",
                "⚡ This is a DRY RUN - no changes will be made"
            ])

            if validation_result.get('requires_confirmation'):
                preview_lines.append("❌ CONFIRMATION REQUIRED before proceeding")

            return Success("\n".join(preview_lines))

        except Exception as e:
            return Failure(f"Preview generation failed: {str(e)}")

    def _analyze_script(self, script: str, script_type: str) -> dict:
        """
        Analyze script for validation purposes.
        """
        script_lower = script.lower()

        analysis = {
            'syntax_valid': True,
            'has_destructive_ops': False,
            'has_untested_patterns': False,
            'estimated_rows_affected': 0
        }

        # Check for destructive operations
        destructive_patterns = [
            'drop ', 'delete ', 'truncate ', 'alter table.*drop',
            'update.*set.*=.*null', 'exec sp_rename'
        ]
        analysis['has_destructive_ops'] = any(
            pattern in script_lower for pattern in destructive_patterns
        )

        # Check for untested patterns (placeholders)
        untested_patterns = ['dynamic sql', 'xp_cmdshell', 'ole automation']
        analysis['has_untested_patterns'] = any(
            pattern in script_lower for pattern in untested_patterns
        )

        # Basic syntax validation
        if script_type.lower() == 'tsql':
            analysis['syntax_valid'] = ';' in script or 'go' in script_lower
        elif script_type.lower() == 'powershell':
            analysis['syntax_valid'] = script.strip().startswith('$') or '{' in script

        return analysis
