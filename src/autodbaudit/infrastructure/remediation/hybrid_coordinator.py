"""
Hybrid Coordinator micro-component.
Coordinates T-SQL (ODBC) and PowerShell (PSRemote) execution.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    from autodbaudit.infrastructure.psremoting import PSRemotingConnectionManager

@dataclass(frozen=True)
class ExecutionContext:
    """Context for hybrid execution."""
    target_server: str
    target_instance: str
    host_platform: str = "Windows"

@dataclass(frozen=True)
class HybridCoordinator:
    """
    Coordinates hybrid T-SQL and PowerShell execution.
    Railway-oriented: returns Success with coordination result or Failure.
    """

    def coordinate_execution(
        self,
        tsql_script: str | None,
        ps_script: str | None,
        context: ExecutionContext
    ) -> Result[dict, str]:
        """
        Coordinate hybrid execution following priority chain:
        Manual > PSRemote > Cached > T-SQL fallback.
        """
        execution_plan = self._build_execution_plan(
            tsql_script, ps_script, context.host_platform
        )

        if not execution_plan:
            return Failure("No executable scripts provided")

        results = {}

        # Execute T-SQL first (database changes)
        if execution_plan.get('tsql'):
            tsql_result = self._execute_tsql_phase()
            results['tsql'] = tsql_result

        # Execute PowerShell second (OS-level changes)
        if execution_plan.get('powershell'):
            ps_result = self._execute_powershell_phase()
            results['powershell'] = ps_result

        # Check for critical failures
        has_critical_failure = any(
            isinstance(result, Failure) and not result.error.recoverable
            for result in results.values()
            if hasattr(result, 'error')
        )

        if has_critical_failure:
            return Failure("Critical execution failure in hybrid coordination")

        return Success({
            'execution_plan': execution_plan,
            'results': results,
            'coordination_success': True
        })

    def _build_execution_plan(
        self,
        tsql_script: str | None,
        ps_script: str | None,
        host_platform: str
    ) -> dict:
        """Build execution plan based on available scripts and platform."""
        plan = {}

        if tsql_script:
            plan['tsql'] = {'script': tsql_script, 'priority': 1}

        if ps_script and host_platform == "Windows":
            plan['powershell'] = {'script': ps_script, 'priority': 2}
        elif ps_script and host_platform != "Windows":
            # Log that PS script is omitted for non-Windows
            reason = f'Unsupported platform: {host_platform}'
            plan['powershell'] = {'omitted': True, 'reason': reason}

        return plan

    def _execute_tsql_phase(self) -> Result[bool, str]:
        """Execute T-SQL phase (placeholder - will integrate with ODBC)."""
        # TODO: Integrate with actual ODBC execution
        return Success(True)

    def _execute_powershell_phase(self) -> Result[bool, str]:
        """Execute PowerShell phase using PS remoting manager."""
        # TODO: Integrate with PS remoting execution
        return Success(True)
