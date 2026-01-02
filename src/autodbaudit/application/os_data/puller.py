"""
OS Data Puller - Ultra-Granular Refactored.

Modern facade over micro-components for OS data collection.
Maintains backward compatibility while using Railway-oriented architecture.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from autodbaudit.application.os_data.orchestrator import OsDataOrchestrator

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
    Modern facade for OS data collection.
    Delegates to ultra-granular micro-components.
    """

    def get_os_data(
        self,
        target_id: str,
        can_pull_os_data: bool = False,
        manual_data: dict[str, Any] | None = None,
    ) -> OsDataResult:
        """
        Get OS data using micro-component orchestration.

        Args:
            target_id: Unique identifier for target (server|instance)
            can_pull_os_data: Whether PSRemote access is available
            manual_data: User-provided manual data (highest priority)

        Returns:
            OsDataResult with source, data, and metadata
        """
        orchestrator = OsDataOrchestrator()
        result = orchestrator.orchestrate_collection(
            target_id=target_id,
            can_pull_os_data=can_pull_os_data,
            manual_data=manual_data
        )

        # Import the result types for proper type checking
        from autodbaudit.infrastructure.remediation.results import Success, Failure

        if isinstance(result, Success):
            source = "manual" if manual_data else "psremote" if can_pull_os_data else "cached"
            return OsDataResult(
                source=source,
                data=result.value,
                is_authoritative=source in ("manual", "psremote"),
                stale=source == "cached",
                collected_at=datetime.now(timezone.utc),
            )
        else:  # isinstance(result, Failure)
            return OsDataResult(
                source="none",
                data=None,
                is_authoritative=False,
                warning=result.error,
            )
