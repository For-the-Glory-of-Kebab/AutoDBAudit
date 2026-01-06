"""
Shared helpers for target configuration scripts.
"""

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def run_and_capture(server_name: str, script: str, runner: Callable[[str], object]) -> Optional[str]:
    """Run a script and return stdout stripped, or None on failure."""
    try:
        result = runner(script)
        if getattr(result, "returncode", 1) != 0:
            logger.warning("Failed to capture state on %s: %s", server_name, getattr(result, "stderr", ""))
            return None
        return (getattr(result, "stdout", "") or "").strip()
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Error capturing state on %s: %s", server_name, exc)
        return None
