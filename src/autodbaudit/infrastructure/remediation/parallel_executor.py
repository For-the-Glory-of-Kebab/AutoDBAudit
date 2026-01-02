"""
Parallel Executor micro-component.
Executes remediation across multiple targets concurrently.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from typing import Callable, TYPE_CHECKING
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    from autodbaudit.infrastructure.remediation.results import ScriptResult

@dataclass(frozen=True)
class ParallelExecutor:
    """
    Executes remediation operations across multiple targets in parallel.
    Railway-oriented: returns Success with execution results or Failure.
    """

    def execute_parallel(
        self,
        targets: list[dict],
        execution_func: Callable[[dict], ScriptResult],
        max_workers: int = 4
    ) -> Result[list[ScriptResult], str]:
        """
        Execute remediation function across targets in parallel.
        Returns Success with list of results or Failure with error.
        """
        if not targets:
            return Success([])

        if max_workers < 1:
            return Failure("Invalid max_workers value")

        results = []

        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all tasks
                future_to_target = {
                    executor.submit(execution_func, target): target
                    for target in targets
                }

                # Collect results as they complete
                for future in as_completed(future_to_target):
                    target = future_to_target[future]
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout
                        results.append(result)
                    except TimeoutError:
                        server = target.get('server', 'unknown')
                        results.append(Failure(f"Timeout executing for target: {server}"))
                    except Exception as e:
                        server = target.get('server', 'unknown')
                        results.append(Failure(f"Execution failed for target {server}: {str(e)}"))

            return Success(results)

        except Exception as e:
            return Failure(f"Parallel execution failed: {str(e)}")

    def validate_dependencies(
        self,
        target_results: list[ScriptResult]
    ) -> Result[bool, str]:
        """
        Validate that target executions don't have conflicting dependencies.
        Returns Success if all validations pass or Failure with conflicts.
        """
        # Check for critical failures that should stop all execution
        critical_failures = [
            result for result in target_results
            if isinstance(result, Failure) and not result.recoverable
        ]

        if critical_failures:
            return Failure(f"Critical failures detected: {len(critical_failures)} targets failed")

        # Check for dependency conflicts (placeholder for future logic)
        # e.g., if target A depends on target B's success

        return Success(True)
