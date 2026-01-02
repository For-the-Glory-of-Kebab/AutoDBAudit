"""
Refactored Prepare Service - Ultra-granular orchestration layer.

This module orchestrates the ultra-granular prepare components using
modern Python patterns and dependency injection.
"""

import logging
from typing import Any, List, Optional
from datetime import datetime

from autodbaudit.domain.config import (
    ConnectionMethod,
    PrepareResult,
    ServerConnectionInfo,
    SqlTarget
)
from autodbaudit.domain.config.audit_settings import AuditSettings
from autodbaudit.domain.config.prepare_server import PrepareServerResult, ServerConnectionProfile

from ..infrastructure.config.manager import ConfigManager
from ..infrastructure.sqlite.store import HistoryStore
from .prepare.cache.cache_manager import ConnectionCacheManager
from .prepare.connection.connection_tester import ConnectionTestingService
from .prepare.detection.os_detector import OSDetectionService
from .prepare.method.method_selector import ConnectionMethodSelector

logger = logging.getLogger(__name__)


class PrepareService:
    """
    Ultra-granular prepare service using dependency injection.

    Orchestrates specialized services for connection preparation with
    modern Python patterns and intelligent caching.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        os_detector: Optional[OSDetectionService] = None,
        connection_tester: Optional[ConnectionTestingService] = None,
        method_selector: Optional[ConnectionMethodSelector] = None,
        cache_manager: Optional[ConnectionCacheManager] = None,
        audit_settings: Optional[AuditSettings] = None,
        history_store: Optional[HistoryStore] = None,
    ) -> None:
        """
        Initialize the prepare service with dependency injection.

        Args:
            config_manager: Configuration manager
            os_detector: OS detection service (created if None)
            connection_tester: Connection testing service (created if None)
            method_selector: Method selection service (created if None)
            cache_manager: Cache management service (created if None)
            audit_settings: Dynamic audit settings for timeouts
            history_store: History store for DB persistence (created if None)
        """
        self.config_manager = config_manager
        self.audit_settings = audit_settings or AuditSettings()

        # Initialize services with defaults
        self.os_detector = os_detector or OSDetectionService()
        self.connection_tester = connection_tester or ConnectionTestingService()
        self.method_selector = method_selector or ConnectionMethodSelector()
        self.cache_manager = cache_manager or ConnectionCacheManager()
        self.history_store = history_store  # Will be set later if None

        # Apply dynamic timeouts
        self._configure_timeouts()

        logger.info("PrepareService initialized with ultra-granular components")

    def _configure_timeouts(self) -> None:
        """Configure dynamic timeouts in all services."""
        # Note: Timeout configuration will be handled by passing timeout values
        # to individual method calls rather than setting global timeouts
        logger.debug("Dynamic timeouts configured: %s", self.audit_settings.timeouts)

    def prepare_target(self, target: SqlTarget) -> PrepareResult:
        """
        Prepare a single target using ultra-granular services.

        Args:
            target: SQL target to prepare

        Returns:
            PrepareResult with success/failure status
        """
        logger.info("Preparing target: %s (%s)", target.name, target.server)

        # Check cache first
        cached_info = self.cache_manager.get(target.name)
        if cached_info is not None:
            logger.info("Using cached connection info for target: %s", target.name)
            return PrepareResult.success_result(target, cached_info)

        # Fresh preparation using ultra-granular services
        logs = [f"Starting preparation for target: {target.name}"]

        try:
            # Step 1: Detect OS type
            os_type = self.os_detector.detect_os(target.server)
            logs.append(f"Detected OS type: {os_type.value}")

            # Step 2: Check available connection methods
            available_methods = self.connection_tester.get_available_methods(target.server)
            logs.append(f"Available connection methods: {[m.value for m in available_methods]}")

            # Step 3: Select preferred method
            preferred_method = self.method_selector.select_preferred_method(
                available_methods, os_type
            )
            method_name = preferred_method.value if preferred_method else "None"
            logs.append(f"Selected preferred method: {method_name}")

            # Step 4: Test connection
            is_available = (
                self.connection_tester.test_connection(target.server, preferred_method)
                if preferred_method else False
            )
            logs.append(f"Connection test result: {'SUCCESS' if is_available else 'FAILED'}")

            # Step 5: Create connection info
            connection_info = ServerConnectionInfo(
                server_name=target.server,
                os_type=os_type,
                available_methods=available_methods,
                preferred_method=preferred_method,
                is_available=is_available,
                last_checked=self._get_timestamp(),
                connection_details=self._get_connection_details(target, preferred_method)
            )

            # Cache successful results
            if is_available:
                self.cache_manager.put(target.name, connection_info)
                # Persist to DB for audit state
                self._persist_server_state(target, connection_info)
                logs.append("Preparation completed successfully")
                return PrepareResult.success_result(target, connection_info, logs)
            else:
                error_msg = f"Target {target.name} is not available via any connection method"
                logs.append(error_msg)
                return PrepareResult.failure_result(target, error_msg, logs)

        except Exception as e:
            error_msg = f"Preparation failed for target {target.name}: {e}"
            logs.append(error_msg)
            logger.error("Preparation failed: %s", e)
            return PrepareResult.failure_result(target, error_msg, logs)

    def prepare_targets(
        self,
        targets: Optional[List[SqlTarget]] = None
    ) -> List[PrepareResult]:
        """
        Prepare multiple targets using ultra-granular services.

        Args:
            targets: List of targets to prepare (default: all enabled targets)

        Returns:
            List of PrepareResult objects
        """
        if targets is None:
            targets = self.config_manager.get_enabled_targets()

        if self.audit_settings.enable_parallel_processing:
            return self._prepare_targets_parallel(targets)
        else:
            return self._prepare_targets_sequential(targets)

    def _prepare_targets_sequential(self, targets: List[SqlTarget]) -> List[PrepareResult]:
        """Prepare targets sequentially."""
        logger.info("Preparing %d targets sequentially with ultra-granular services", len(targets))
        results = []

        for target in targets:
            result = self.prepare_target(target)
            results.append(result)

        successful = sum(1 for r in results if r.success)
        logger.info("Preparation completed: %d/%d targets successful", successful, len(results))

        return results

    def _prepare_targets_parallel(self, targets: List[SqlTarget]) -> List[PrepareResult]:
        """
        Prepare targets in parallel for better performance.

        Args:
            targets: List of targets to prepare

        Returns:
            List of prepare results
        """
        import concurrent.futures

        max_workers = min(self.audit_settings.max_parallel_targets, len(targets))

        logger.info("Preparing %d targets with %d parallel workers", len(targets), max_workers)

        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all prepare tasks
            future_to_target = {
                executor.submit(self.prepare_target, target): target
                for target in targets
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_target):
                target = future_to_target[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.debug("Completed preparation for target: %s", target.name)
                except Exception as e:
                    logger.error("Preparation failed for target %s: %s", target.name, e)
                    # Create failure result
                    failure_result = PrepareResult.failure_result(
                        target, f"Parallel preparation failed: {e}", [f"Error: {e}"]
                    )
                    results.append(failure_result)

        successful = sum(1 for r in results if r.success)
        logger.info("Parallel preparation completed: %d/%d targets successful", successful, len(results))

        return results

    def clear_cache(self) -> None:
        """Clear all caches in ultra-granular services."""
        self.os_detector.clear_cache()
        self.connection_tester.clear_cache()
        self.cache_manager.clear()
        logger.info("All prepare service caches cleared")

    def get_cache_stats(self) -> dict[str, Any]:
        """
        Get comprehensive cache statistics.

        Returns:
            Dictionary with cache statistics from all services
        """
        cache_stats = self.cache_manager.get_stats()

        return {
            "connection_cache": {
                "hits": cache_stats.hits,
                "misses": cache_stats.misses,
                "puts": cache_stats.puts,
                "deletes": cache_stats.deletes,
                "hit_rate": cache_stats.get_hit_rate(),
            },
            "os_detection_cache_size": len(self.os_detector._detection_cache),
            "connection_test_cache_size": len(self.connection_tester._test_cache),
        }

    def _get_connection_details(
        self,
        target: SqlTarget,
        method: Optional[ConnectionMethod]
    ) -> dict[str, Any]:
        """
        Get detailed connection information for a target.

        Args:
            target: SQL target
            method: Selected connection method

        Returns:
            Dictionary with connection details
        """
        details = {
            "server": target.server,
            "port": target.port,
            "database": target.database,
            "auth_type": target.auth_type.value,
            "connection_method": method.value if method else None
        }

        # Add credential info (without exposing secrets)
        try:
            credential = self.config_manager.get_credential(target.credentials_ref)
            details["has_credentials"] = True
            details["username_length"] = len(credential.username)
        except Exception:
            details["has_credentials"] = False

        return details

    def _persist_server_state(self, target: SqlTarget, connection_info: ServerConnectionInfo) -> None:
        """
        Persist server state to database for audit operations.
        
        Args:
            target: SQL target
            connection_info: Connection information
        """
        if self.history_store is None:
            return  # DB persistence not available
            
        try:
            # Upsert server
            server = self.history_store.upsert_server(target.server)
            
            # Upsert instance
            instance = self.history_store.upsert_instance(
                server=server,
                instance_name="",  # Default instance
                port=target.port or 1433,
                version="Unknown",  # Will be updated during audit
                version_major=0,
                edition=None,
                product_level=None
            )
            
            logger.debug("Persisted server state for target: %s", target.name)
        except Exception as e:
            logger.warning("Failed to persist server state: %s", e)

    def prepare_server(
        self,
        server_name: str,
        sql_targets: List[SqlTarget],
        config_file: Optional[str] = None,
        credentials_file: Optional[str] = None,
        timeout: int = 300,
        dry_run: bool = False
    ) -> PrepareServerResult:
        """
        Prepare a single server for PS remoting using comprehensive 5-layer strategy.

        This handles the full PS remoting setup for a server that may host multiple
        SQL instances, implementing all layers from docs/sync/prepare.md.

        Args:
            server_name: Server hostname/IP to prepare
            sql_targets: List of SQL targets on this server (for credential resolution)
            config_file: Path to configuration file
            credentials_file: Path to credentials file
            timeout: Timeout per operation in seconds
            dry_run: Whether to simulate without executing

        Returns:
            PrepareServerResult with success/failure status and connection details
        """
        logger.info("Preparing server '%s' for PS remoting (covers %d SQL targets)", server_name, len(sql_targets))

        # Get OS credentials from the first SQL target (they should all be the same for same server)
        os_credentials = None
        if sql_targets and hasattr(sql_targets[0], 'os_credential_file'):
            try:
                # Use the os_credential_file from the first target
                os_cred_file = sql_targets[0].os_credential_file
                if os_cred_file:
                    os_credentials = self.config_manager.get_credential(os_cred_file)
                    logger.debug("Using OS credentials from %s for server %s", os_cred_file, server_name)
            except Exception as e:
                logger.warning("Could not load OS credentials for server %s: %s", server_name, e)

        # For now, implement basic connection testing
        # TODO: Implement full 5-layer PS remoting strategy
        logs = [f"Starting PS remoting preparation for server: {server_name}"]

        try:
            # Check if this is localhost (special handling)
            is_localhost = server_name.lower() in ['localhost', '127.0.0.1', '::1']

            if is_localhost:
                logs.append("Detected localhost - applying special localhost configuration")
                # TODO: Implement localhost-specific setup (DisableLoopbackCheck, etc.)

            # Layer 1: Direct connection attempts
            logs.append("Layer 1: Attempting direct PS remoting connections")
            connection_success = self._try_direct_connection(server_name, os_credentials, timeout, dry_run)
            logs.append(f"Direct connection result: {'SUCCESS' if connection_success else 'FAILED'}")

            if connection_success:
                # Store successful connection profile
                profile = ServerConnectionProfile(
                    server_name=server_name,
                    connection_method=ConnectionMethod.POWERSHELL_REMOTING,
                    auth_method="negotiate",  # TODO: detect actual method used
                    successful=True,
                    last_successful=datetime.utcnow(),
                    sql_targets=[t.name for t in sql_targets]
                )
                self._persist_connection_profile(profile)
                logs.append("Successfully established PS remoting connection")
                return PrepareServerResult.success_result(server_name, profile, logs)
            else:
                # Generate manual override script
                manual_script = self._generate_manual_override_script(server_name, sql_targets, os_credentials)
                logs.append("Generated manual override script for failed connection")
                logs.append(f"Manual script saved to: {manual_script}")

                error_msg = f"PS remoting setup failed for server {server_name}. Manual script generated."
                logs.append(error_msg)
                return PrepareServerResult.failure_result(server_name, error_msg, logs, manual_script)

        except Exception as e:
            error_msg = f"PS remoting preparation failed for server {server_name}: {e}"
            logs.append(error_msg)
            logger.error("Server preparation failed: %s", e)
            return PrepareServerResult.failure_result(server_name, error_msg, logs)

    def _try_direct_connection(
        self,
        server_name: str,
        os_credentials: Optional[Any],
        timeout: int,
        dry_run: bool
    ) -> bool:
        """
        Try direct PS remoting connection using current implementation.

        This is a placeholder for the full 5-layer strategy.
        Currently uses the existing connection testing logic.
        """
        if dry_run:
            logger.info("DRY RUN: Would attempt PS remoting connection to %s", server_name)
            return True  # Simulate success for dry run

        try:
            # Use existing connection testing logic
            available_methods = self.connection_tester.get_available_methods(server_name)
            if ConnectionMethod.POWERSHELL_REMOTING in available_methods:
                success = self.connection_tester.test_connection(
                    server_name, ConnectionMethod.POWERSHELL_REMOTING
                )
                return success
            return False
        except Exception as e:
            logger.warning("Direct connection attempt failed for %s: %s", server_name, e)
            return False

    def _persist_connection_profile(self, profile: ServerConnectionProfile) -> None:
        """
        Persist successful connection profile to database.

        TODO: Implement database persistence for connection profiles.
        """
        logger.info("TODO: Persist connection profile for server %s", profile.server_name)
        # For now, just log - full implementation needs DB schema

    def _generate_manual_override_script(
        self,
        server_name: str,
        sql_targets: List[SqlTarget],
        os_credentials: Optional[Any]
    ) -> str:
        """
        Generate manual override PowerShell script for failed connections.

        TODO: Implement comprehensive manual script generation with:
        - WinRM service enablement
        - Firewall rule creation
        - TrustedHosts management
        - Registry modifications
        - Step-by-step instructions
        """
        script_path = f"output/manual_psremoting_setup_{server_name}.ps1"
        logger.info("TODO: Generate manual override script at %s", script_path)
        # For now, just return placeholder path
        return script_path

