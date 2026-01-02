"""
PSRemote Invoker micro-component.
Handles PSRemote OS data collection invocation.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    from autodbaudit.infrastructure.psremoting.executor.script_executor import ExecutionResult

logger = logging.getLogger(__name__)

class PsRemoteOsDataInvoker:
    """
    Invokes PSRemote for OS data collection.
    Railway-oriented: returns Success with data or Failure.
    """

    def invoke_collection(
        self,
        hostname: str,
        instance_name: str,
        username: str | None = None,
        password: str | None = None
    ) -> Result[dict, str]:
        """
        Invoke PSRemote OS data collection.
        Returns Success with collected data or Failure on error.
        """
        try:
            from autodbaudit.infrastructure.psremoting.executor.script_executor import ScriptExecutor
        except ImportError:
            return Failure("pywinrm not available, PSRemote disabled")

        logger.info("Invoking PSRemote for %s (instance: %s)", hostname, instance_name)

        try:
            executor = ScriptExecutor.from_config(
                hostname=hostname,
                username=username,
                password=password,
            )

            # Get the execution result
            execution_result = executor.get_os_data(instance_name=instance_name)
            executor.close()

            if execution_result.success and execution_result.data:
                logger.info("✓ PSRemote data collected from %s", hostname)
                return Success(execution_result.data)
            else:
                error_msg = execution_result.error or "Unknown PSRemote error"
                logger.warning("PSRemote failed for %s: %s", hostname, error_msg)
                return Failure(f"PSRemote collection failed: {error_msg}")

        except Exception as e:
            logger.exception("PSRemote exception for %s: %s", hostname, e)
            return Failure(f"PSRemote invocation failed: {str(e)}")
