"""
OS Data Orchestrator micro-component.
Coordinates OS data collection with priority fallback chain.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from autodbaudit.domain.targets.parser import TargetParser
from autodbaudit.infrastructure.cache.os_data_manager import OsDataCacheManager
from autodbaudit.infrastructure.credentials.repository import CredentialRepository
from autodbaudit.infrastructure.psremoting.executor.os_data_invoker import PsRemoteOsDataInvoker
from autodbaudit.infrastructure.remediation.results import Result, Success, Failure

if TYPE_CHECKING:
    from autodbaudit.domain.targets.parser import ParsedTarget
    from autodbaudit.infrastructure.cache.os_data_manager import CachedOsData

logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class OsDataOrchestrator:
    """
    Orchestrates OS data collection with priority fallback.
    Railway-oriented: returns Success with result or Failure.
    """

    def orchestrate_collection(
        self,
        target_id: str,
        can_pull_os_data: bool = False,
        manual_data: dict | None = None,
    ) -> Result[dict, str]:
        """
        Orchestrate OS data collection with priority chain:
        1. Manual data (highest priority)
        2. PSRemote live data (if enabled)
        3. Cached data (fallback)
        4. Failure (no data available)

        Returns Success with data or Failure with reason.
        """
        # Priority 1: Manual data always wins
        if manual_data:
            logger.info("Using manual OS data for %s", target_id)
            return Success(manual_data)

        # Priority 2: PSRemote live data
        if can_pull_os_data:
            psremote_result = self._try_psremote_collection(target_id)
            if isinstance(psremote_result, Success):
                return psremote_result

        # Priority 3: Cached data
        cache_result = self._try_cached_collection(target_id)
        if isinstance(cache_result, Success):
            return cache_result

        # Priority 4: No data available
        return Failure(f"No OS data available for {target_id} - manual entry required")

    def _try_psremote_collection(self, target_id: str) -> Result[dict, str]:
        """Attempt PSRemote data collection."""
        try:
            # Parse target
            parser = TargetParser()
            parse_result = parser.parse_target_id(target_id)

            if isinstance(parse_result, Failure):
                return parse_result

            parsed_target = parse_result.value

            # Get credentials
            cred_repo = CredentialRepository()

            username_result = cred_repo.get_username(parsed_target.hostname)
            if isinstance(username_result, Failure):
                return username_result

            password_result = cred_repo.get_password(parsed_target.hostname)
            if isinstance(password_result, Failure):
                return password_result

            # Invoke PSRemote collection
            invoker = PsRemoteOsDataInvoker()
            invoke_result = invoker.invoke_collection(
                hostname=parsed_target.hostname,
                instance_name=parsed_target.instance_name,
                username=username_result.value,
                password=password_result.value
            )

            if isinstance(invoke_result, Success):
                # Cache successful result
                cache_manager = OsDataCacheManager()
                cache_manager.store(target_id, invoke_result.value)

            return invoke_result

        except Exception as e:
            logger.warning("PSRemote collection failed for %s: %s", target_id, e)
            return Failure(f"PSRemote collection failed: {str(e)}")

    def _try_cached_collection(self, target_id: str) -> Result[dict, str]:
        """Attempt cached data retrieval."""
        try:
            cache_manager = OsDataCacheManager()
            cache_result = cache_manager.retrieve(target_id)

            if isinstance(cache_result, Failure):
                return cache_result

            cached_data = cache_result.value
            if cached_data:
                logger.info("Using cached OS data for %s (collected: %s)",
                          target_id, cached_data.collected_at.isoformat())
                return Success(cached_data.data)

            return Failure("No cached data available")

        except Exception as e:
            return Failure(f"Cache retrieval failed: {str(e)}")
