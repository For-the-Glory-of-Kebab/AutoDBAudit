"""
Layer 5 manual override handling for PS remoting.
"""

from typing import List, Callable

from ..models import ConnectionAttempt, PSRemotingResult
from .manual_support import (
    generate_manual_setup_scripts,
    generate_revert_scripts,
    generate_troubleshooting_report,
)


def run_manual_layer(
    server_name: str,
    attempts: List[ConnectionAttempt],
    timestamp_provider: Callable[[], str],
    revert_scripts: list[str],
) -> PSRemotingResult:
    """Generate manual remediation artifacts and result payload."""
    troubleshooting_report = generate_troubleshooting_report(
        server_name, attempts, timestamp_provider
    )
    manual_scripts = generate_manual_setup_scripts(server_name)
    rendered_revert = generate_revert_scripts(revert_scripts)

    return PSRemotingResult(
        success=False,
        session=None,
        error_message="Layer 5: Manual intervention required",
        attempts_made=attempts,
        duration_ms=0,
        troubleshooting_report=troubleshooting_report,
        manual_setup_scripts=manual_scripts,
        revert_scripts=rendered_revert,
    )
