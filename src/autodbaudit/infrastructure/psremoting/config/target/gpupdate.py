"""
Force Group Policy application on the target host.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def trigger_gpupdate(server_name: str, runner: Callable[[str], object]) -> bool:
    """Invoke a remote gpupdate to apply pending policy changes."""
    script = f"""
Invoke-Command -ComputerName '{server_name}' -ScriptBlock {{
    gpupdate /target:computer /force | Out-Null
    "gpupdate_completed"
}}
"""
    try:
        result = runner(script)
        return getattr(result, "returncode", 1) == 0
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Failed to trigger gpupdate on %s: %s", server_name, exc)
        return False
