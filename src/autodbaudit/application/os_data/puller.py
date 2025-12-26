"""
OS Data Puller.

Pulls OS-level data with fallback chain:
1. Manual user input (highest priority)
2. PSRemote live data (if can_pull_os_data = true)
3. Cached data (if PSRemote unavailable)
4. None (return warning)

Data pulled:
- Client Protocols (TCP, Named Pipes, Shared Memory)
- Service Accounts (actual account from WMI)
- OS Audit Policies
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


@dataclass
class OsDataResult:
    """Result from OS data collection."""

    source: Literal["manual", "psremote", "cached", "none"]
    data: dict[str, Any] | None = None
    is_authoritative: bool = False
    stale: bool = False
    warning: str | None = None
    collected_at: datetime | None = None


@dataclass
class OsDataPuller:
    """
    Pulls OS-level data with priority fallback.

    Priority Chain:
    1. Manual user input (always wins)
    2. PSRemote live data (if can_pull_os_data)
    3. Cached data (last known good)
    4. None (return warning)
    """

    cache_dir: Path = field(default_factory=lambda: Path("output/os_data_cache"))

    def __post_init__(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_os_data(
        self,
        target_id: str,
        can_pull_os_data: bool = False,
        manual_data: dict[str, Any] | None = None,
    ) -> OsDataResult:
        """
        Get OS data with proper priority fallback.

        Args:
            target_id: Unique identifier for target (server|instance)
            can_pull_os_data: Whether PSRemote access is available
            manual_data: User-provided manual data (highest priority)

        Returns:
            OsDataResult with source, data, and metadata
        """
        # Priority 1: Manual user input always wins
        if manual_data:
            logger.info("Using manual OS data for %s", target_id)
            return OsDataResult(
                source="manual",
                data=manual_data,
                is_authoritative=True,
                collected_at=datetime.now(timezone.utc),
            )

        # Priority 2: PSRemote live data
        if can_pull_os_data:
            try:
                live_data = self._invoke_psremote(target_id)
                if live_data:
                    # Cache for future fallback
                    self._cache_data(target_id, live_data)
                    return OsDataResult(
                        source="psremote",
                        data=live_data,
                        is_authoritative=True,
                        collected_at=datetime.now(timezone.utc),
                    )
            except Exception as e:
                logger.warning("PSRemote failed for %s: %s, falling back", target_id, e)

        # Priority 3: Cached data
        cached = self._load_cached(target_id)
        if cached:
            logger.info("Using cached OS data for %s (stale)", target_id)
            return OsDataResult(
                source="cached",
                data=cached["data"],
                is_authoritative=False,
                stale=True,
                collected_at=datetime.fromisoformat(cached["collected_at"]),
            )

        # Priority 4: No data available
        logger.warning("No OS data available for %s", target_id)
        return OsDataResult(
            source="none",
            data=None,
            is_authoritative=False,
            warning="No OS data available - manual entry required",
        )

    def _invoke_psremote(self, target_id: str) -> dict[str, Any] | None:
        """
        Invoke PSRemote to collect OS data.

        TODO: Implement actual PSRemote invocation using pywinrm or subprocess.
        Returns None on failure.
        """
        # Placeholder - actual implementation will use:
        # 1. Get access status from AccessPreparationService
        # 2. Invoke Get-SqlServerOSData.ps1 via Invoke-Command
        # 3. Parse JSON result
        logger.debug("PSRemote invocation for %s - not yet implemented", target_id)
        return None

    def _cache_data(self, target_id: str, data: dict[str, Any]) -> None:
        """Cache OS data for fallback."""
        safe_id = target_id.replace("\\", "_").replace("|", "_")
        cache_path = self.cache_dir / f"{safe_id}.json"

        cache_obj = {
            "target_id": target_id,
            "data": data,
            "collected_at": datetime.now(timezone.utc).isoformat(),
        }

        cache_path.write_text(json.dumps(cache_obj, indent=2), encoding="utf-8")
        logger.debug("Cached OS data for %s", target_id)

    def _load_cached(self, target_id: str) -> dict[str, Any] | None:
        """Load cached OS data if available."""
        safe_id = target_id.replace("\\", "_").replace("|", "_")
        cache_path = self.cache_dir / f"{safe_id}.json"

        if not cache_path.exists():
            return None

        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to load cache for %s: %s", target_id, e)
            return None
