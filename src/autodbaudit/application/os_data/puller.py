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
        Invoke PSRemote to collect OS data using ScriptExecutor.

        Args:
            target_id: Format "hostname|instance_name" or "hostname\\instance"

        Returns:
            OS data dict or None on failure
        """
        try:
            from autodbaudit.infrastructure.psremote import ScriptExecutor
        except ImportError:
            logger.warning("pywinrm not available, PSRemote disabled")
            return None

        # Parse target_id: "hostname|instance" or "hostname\\instance"
        if "|" in target_id:
            hostname, instance_name = target_id.split("|", 1)
        elif "\\" in target_id:
            hostname, instance_name = target_id.split("\\", 1)
        else:
            hostname = target_id
            instance_name = "MSSQLSERVER"

        # Get credentials from stored access status (if available)
        username = self._get_cached_username(hostname)
        password = self._get_cached_password(hostname)

        logger.info("Invoking PSRemote for %s (instance: %s)", hostname, instance_name)

        try:
            executor = ScriptExecutor.from_config(
                hostname=hostname,
                username=username,
                password=password,
            )

            result = executor.get_os_data(instance_name=instance_name)
            executor.close()

            if result.success and result.data:
                logger.info("✓ PSRemote data collected from %s", hostname)
                return result.data
            else:
                logger.warning("PSRemote failed for %s: %s", hostname, result.error)
                return None

        except Exception as e:
            logger.exception("PSRemote exception for %s: %s", hostname, e)
            return None

    def _get_cached_username(self, hostname: str) -> str | None:
        """Get cached username for hostname from access status."""
        # Try to load from access status DB
        try:
            from autodbaudit.infrastructure.sqlite.store import HistoryStore

            store = HistoryStore(Path("output/audit_history.db"))

            # Query access_status table for credentials
            cursor = store.conn.execute(
                "SELECT username FROM access_status WHERE server_name = ?", (hostname,)
            )
            row = cursor.fetchone()
            store.close()

            if row and row[0]:
                return row[0]
        except Exception:
            pass
        return None

    def _get_cached_password(self, hostname: str) -> str | None:
        """Get cached password - in practice this should use secure storage."""
        # For now, we rely on Windows credential manager or environment
        # In production, integrate with credential_loader
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
