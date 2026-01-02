"""
Cache Manager micro-component.
Handles OS data caching with fallback logic.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

logger = logging.getLogger(__name__)

@dataclass
class CachedOsData:
    """Cached OS data with metadata."""
    target_id: str
    data: dict[str, Any]
    collected_at: datetime

@dataclass(frozen=True)
class OsDataCacheManager:
    """
    Manages OS data caching with safe file operations.
    Railway-oriented: returns Success with cached data or Failure.
    """

    cache_dir: Path = field(default_factory=lambda: Path("output/os_data_cache"))

    def __post_init__(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def store(self, target_id: str, data: dict[str, Any]) -> Result[bool, str]:
        """
        Store OS data in cache.
        Returns Success on successful storage or Failure on error.
        """
        try:
            safe_id = self._sanitize_target_id(target_id)
            cache_path = self.cache_dir / f"{safe_id}.json"

            cache_obj = {
                "target_id": target_id,
                "data": data,
                "collected_at": datetime.now(timezone.utc).isoformat(),
            }

            cache_path.write_text(
                json.dumps(cache_obj, indent=2, default=str),
                encoding="utf-8"
            )

            logger.debug("Cached OS data for %s", target_id)
            return Success(True)

        except Exception as e:
            return Failure(f"Failed to cache data for {target_id}: {str(e)}")

    def retrieve(self, target_id: str) -> Result[CachedOsData | None, str]:
        """
        Retrieve cached OS data.
        Returns Success with cached data or None if not found, or Failure on error.
        """
        try:
            safe_id = self._sanitize_target_id(target_id)
            cache_path = self.cache_dir / f"{safe_id}.json"

            if not cache_path.exists():
                return Success(None)

            cache_content = json.loads(
                cache_path.read_text(encoding="utf-8")
            )

            cached_data = CachedOsData(
                target_id=cache_content["target_id"],
                data=cache_content["data"],
                collected_at=datetime.fromisoformat(cache_content["collected_at"])
            )

            return Success(cached_data)

        except Exception as e:
            return Failure(f"Failed to retrieve cached data for {target_id}: {str(e)}")

    def _sanitize_target_id(self, target_id: str) -> str:
        """Sanitize target ID for safe file naming."""
        return target_id.replace("\\", "_").replace("|", "_").replace("/", "_")
