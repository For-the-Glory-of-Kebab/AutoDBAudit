"""
OS Data Module.

Pulls OS-level data via PSRemote with fallback chain:
1. Manual user input (highest priority)
2. PSRemote live data (if can_pull_os_data = true)
3. Cached data (if PSRemote unavailable)
"""

from autodbaudit.application.os_data.puller import OsDataPuller, OsDataResult

__all__ = ["OsDataPuller", "OsDataResult"]
