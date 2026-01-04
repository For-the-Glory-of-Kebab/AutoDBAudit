"""
Tracks configuration changes and revert scripts for PS remoting setup.
"""

from typing import List, Dict, Any, Callable


class RevertTracker:
    """Collects change metadata and revert scripts during setup."""

    def __init__(self, timestamp_provider: Callable[[], str]):
        self._timestamp = timestamp_provider
        self._changes: List[Dict[str, Any]] = []
        self._scripts: List[str] = []

    def reset(self) -> None:
        """Clear tracked state."""
        self._changes.clear()
        self._scripts.clear()

    def track_change(self, change_type: str, server: str, details: str) -> None:
        """Record a change for auditing purposes."""
        self._changes.append(
            {
                "type": change_type,
                "server": server,
                "details": details,
                "timestamp": self._timestamp(),
            }
        )

    def add_revert_script(self, script: str) -> None:
        """Store a revert script snippet."""
        self._scripts.append(script)

    @property
    def changes(self) -> List[Dict[str, Any]]:
        """Get recorded changes."""
        return list(self._changes)

    @property
    def scripts(self) -> List[str]:
        """Get collected revert scripts."""
        return list(self._scripts)
