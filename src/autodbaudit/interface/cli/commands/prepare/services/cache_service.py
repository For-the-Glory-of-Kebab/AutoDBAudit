"""
Cache Service - Manages Connection Cache Operations

Handles caching of connection information and credentials.
"""

from typing import List, Optional

from autodbaudit.application.prepare_service import PrepareService
from autodbaudit.infrastructure.config.manager import ConfigManager
from autodbaudit.infrastructure.psremoting.repository import PSRemotingRepository


class CacheService:
    """Service for managing connection cache operations."""

    def __init__(self):
        self.config_manager = ConfigManager()
        self.prepare_service = PrepareService(self.config_manager)
        self.repository = PSRemotingRepository()

    def clear_all_cache(self) -> str:
        """
        Clear all cached connection information.

        Returns:
            Success message or error message
        """
        try:
            # Clear in-memory cache
            self.prepare_service.clear_cache()

            # For now, we don't clear DB cache as it's persistent
            # TODO: Add DB cache clearing if needed

            return "All connection caches cleared successfully"
        except Exception as e:
            return f"Failed to clear cache: {str(e)}"

    def clear_cache(self, targets: List[str]) -> str:
        """
        Clear cache for specific targets.

        Args:
            targets: List of target names to clear from cache

        Returns:
            Success message or error message
        """
        try:
            # Get cache manager from prepare service
            cache_manager = self.prepare_service.cache_manager

            cleared_count = 0
            for target in targets:
                if cache_manager.get(target) is not None:
                    cache_manager.delete(target)
                    cleared_count += 1

            return f"Cleared cache for {cleared_count}/{len(targets)} targets"
        except Exception as e:
            return f"Failed to clear cache: {str(e)}"

    def list_cache(self) -> List[dict]:
        """
        List all cached connection information.

        Returns:
            List of cache entries as dictionaries
        """
        try:
            # Get profiles from database
            profiles = self.repository.get_all_profiles()

            cache_entries = []
            for profile in profiles:
                cache_entries.append({
                    "target": profile.server_name,
                    "status": "connected" if profile.successful else "failed",
                    "last_used": profile.last_successful_attempt or profile.last_attempt or "never",
                    "connection_method": profile.connection_method.value,
                    "auth_method": profile.auth_method or "unknown",
                    "attempts": profile.attempt_count,
                    "sql_targets": profile.sql_targets or []
                })

            # Also include in-memory cache stats
            try:
                cache_stats = self.prepare_service.cache_manager.get_stats()
                cache_entries.append({
                    "target": "memory_cache_stats",
                    "status": "stats",
                    "cache_hits": cache_stats.hits,
                    "cache_misses": cache_stats.misses,
                    "total_entries": cache_stats.puts - cache_stats.deletes
                })
            except:
                pass  # Ignore if stats not available

            return cache_entries
        except Exception as e:
            return [{
                "target": "error",
                "status": "error",
                "error": str(e)
            }]
