"""
Refactored Prepare Service - Ultra-granular orchestration layer.

This module orchestrates the ultra-granular prepare components using
modern Python patterns and dependency injection.
"""

import logging
from pathlib import Path
from typing import Any, List, Optional
from datetime import datetime

from autodbaudit.domain.config import (
    ConnectionMethod,
    PrepareResult,
    ServerConnectionInfo,
    SqlTarget,
    OSType
)
from autodbaudit.domain.config.audit_settings import AuditSettings
from autodbaudit.domain.config.prepare_server import PrepareServerResult, ServerConnectionProfile

from ..infrastructure.config.manager import ConfigManager
from ..infrastructure.psremoting.connection_manager import PSRemotingConnectionManager
from ..infrastructure.psremoting.models import PSRemotingResult
from ..infrastructure.sqlite.store import HistoryStore
from .prepare.cache.cache_manager import ConnectionCacheManager
from .prepare.connection.connection_tester import ConnectionTestingService
from .prepare.detection.os_detector import OSDetectionService
from .prepare.method.method_selector import ConnectionMethodSelector
from .prepare.status_service import PrepareStatusService

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
        connection_manager: Optional[PSRemotingConnectionManager] = None,
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
            connection_manager: PS remoting connection manager for full setup
        """
        self.config_manager = config_manager
        self.audit_settings = audit_settings or AuditSettings()

        # Initialize services with defaults
        self.os_detector = os_detector or OSDetectionService()
        self.connection_tester = connection_tester or ConnectionTestingService()
        self.method_selector = method_selector or ConnectionMethodSelector()
        self.cache_manager = cache_manager or ConnectionCacheManager()
        self.history_store = history_store  # Will be set later if None
        self.connection_manager = connection_manager or PSRemotingConnectionManager()
        self.status_service = PrepareStatusService(
            self.cache_manager,
            self.connection_manager.repository,
            self.connection_manager
        )

        # Apply dynamic timeouts
        self._configure_timeouts()

        logger.info("PrepareService initialized with ultra-granular components")

    @staticmethod
    def _get_timestamp() -> str:
        """Timestamp helper to align with connection manager expectations."""
        return datetime.utcnow().isoformat()

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
        cached_info = self.cache_manager.get(target.server)
        if cached_info is not None:
            logger.info("Using cached connection info for target: %s", target.name)
            return PrepareResult.success_result(target, cached_info)

        # Fresh preparation using ultra-granular services
        logs = [f"Starting preparation for target: {target.name}"]

        try:
            # Step 1: Detect OS type
            os_type = self.os_detector.detect_os(target.server)
            logs.append(f"Detected OS type: {os_type.value}")

            # Step 2: Perform full PS remoting preparation/connection attempt
            ps_result: PSRemotingResult = self.connection_manager.connect_to_server(
                target.server,
                {"os_auth": target.os_auth, "credentials_ref": target.credentials_ref},
                allow_config=True,
            )

            available_methods: List[ConnectionMethod] = []
            for attempt in ps_result.attempts_made:
                if attempt.success and attempt.connection_method:
                    available_methods.append(self._map_method(attempt.connection_method))
            if ps_result.is_success() and ConnectionMethod.POWERSHELL_REMOTING not in available_methods:
                available_methods.append(ConnectionMethod.POWERSHELL_REMOTING)
            preferred_method = available_methods[0] if available_methods else None
            successful_permutations = [
                {
                    "auth_method": a.auth_method,
                    "protocol": a.protocol,
                    "port": a.port,
                    "credential_type": a.credential_type,
                    "layer": a.layer,
                }
                for a in ps_result.attempts_made
                if a.success
            ]
            if ps_result.successful_permutations:
                successful_permutations.extend(ps_result.successful_permutations)

            # Step 3: Create connection info snapshot
            connection_info = ServerConnectionInfo(
                server_name=target.server,
                os_type=os_type,
                available_methods=available_methods,
                preferred_method=preferred_method,
                is_available=ps_result.is_success(),
                last_checked=self._get_timestamp(),
                connection_details={
                    "ps_success": ps_result.is_success(),
                    "ps_error": ps_result.error_message,
                    "attempts": [a.model_dump() for a in ps_result.attempts_made],
                    "successful_permutations": successful_permutations,
                }
            )

            # Cache successful results
            if ps_result.is_success():
                self.cache_manager.put(target.server, connection_info)
                self._persist_server_state(target, connection_info)
                logs.append("PS remoting preparation completed successfully")
                return PrepareResult.success_result(target, connection_info, logs)
            error_msg = f"PS remoting preparation failed: {ps_result.error_message}"
            logs.append(error_msg)
            return PrepareResult.failure_result(target, error_msg, logs)

        except Exception as e:
            error_msg = f"Preparation failed for target {target.name}: {e}"
            logs.append(error_msg)
            logger.error("Preparation failed: %s", e)
            return PrepareResult.failure_result(target, error_msg, logs)

    def prepare_targets(
        self,
        targets: Optional[List[SqlTarget]] = None,
        rerun_failed_once: bool = True,
    ) -> List[PrepareResult]:
        """
        Prepare multiple targets using ultra-granular services.

        Args:
            targets: List of targets to prepare (default: all enabled targets)
            rerun_failed_once: Whether to rerun failed servers once to detect manual fixes

        Returns:
            List of PrepareResult objects
        """
        if targets is None:
            targets = self.config_manager.get_enabled_targets()

        if self.audit_settings.enable_parallel_processing:
            results = self._prepare_targets_parallel(targets)
        else:
            results = self._prepare_targets_sequential(targets)

        if rerun_failed_once:
            failed = [res.target for res in results if not res.success]  # type: ignore[attr-defined]
            if failed:
                logger.info("Retrying %d failed targets to detect manual fixes...", len(failed))
                retry_results = (
                    self._prepare_targets_parallel(failed)
                    if self.audit_settings.enable_parallel_processing
                    else self._prepare_targets_sequential(failed)
                )
                # Replace old results with retry results for those targets
                retry_map = {res.target.name: res for res in retry_results}  # type: ignore[attr-defined]
                results = [
                    retry_map.get(res.target.name, res)  # type: ignore[attr-defined]
                    for res in results
                ]

        return results

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
        logger.info(
            "Parallel preparation completed: %d/%d targets successful",
            successful,
            len(results)
        )

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

    def _persist_server_state(
        self,
        target: SqlTarget,
        connection_info: ServerConnectionInfo
    ) -> None:
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
            self.history_store.upsert_instance(
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
        logger.info(
            "Preparing server '%s' for PS remoting (covers %d SQL targets)",
            server_name,
            len(sql_targets)
        )

        logs = [f"Starting PS remoting preparation for server: {server_name}"]

        os_type = self.os_detector.detect_os(server_name)
        logs.append(f"Detected OS type: {os_type.value}")
        if os_type != OSType.WINDOWS:
            error_msg = (
                f"PS remoting setup skipped: server {server_name} appears to be {os_type.value}. "
                "Use T-SQL-only/SSH workflows instead."
            )
            logs.append(error_msg)
            return PrepareServerResult.failure_result(server_name, error_msg, logs)

        credentials_payload = self._build_credentials_payload(sql_targets, credentials_file)
        allow_config = not dry_run

        try:
            result: PSRemotingResult = self.connection_manager.connect_to_server(
                server_name=server_name,
                credentials=credentials_payload,
                allow_config=allow_config
            )

            logs.append(f"Connection attempts: {len(result.attempts_made)}")

            if result.is_success() and result.session:
                session_profile = result.session.connection_profile
                profile = ServerConnectionProfile(
                    server_name=session_profile.server_name,
                    connection_method=ConnectionMethod.POWERSHELL_REMOTING,
                    auth_method=str(session_profile.auth_method),
                    successful=True,
                    last_successful=datetime.utcnow(),
                    sql_targets=[t.name for t in sql_targets],
                    port=session_profile.port
                )
                self._persist_connection_profile(profile)
                logs.append("PS remoting connection established and persisted")
                return PrepareServerResult.success_result(server_name, profile, logs)

            manual_script_path = None
            if result.manual_setup_scripts:
                manual_script_path = self._save_manual_script(
                    server_name,
                    result.manual_setup_scripts
                )
                logs.append(
                    f"Manual setup script generated at {manual_script_path}"
                )
            if result.troubleshooting_report:
                logs.append("Troubleshooting report generated for failed connection")

            error_msg = result.error_message or "PS remoting setup failed"
            return PrepareServerResult.failure_result(
                server_name,
                error_msg,
                logs,
                manual_script_path
            )

        except Exception as e:
            error_msg = f"PS remoting preparation failed for server {server_name}: {e}"
            logs.append(error_msg)
            logger.error("Server preparation failed: %s", e)
            return PrepareServerResult.failure_result(server_name, error_msg, logs)

    def revert_server(
        self,
        server_name: str,
        sql_targets: Optional[List[SqlTarget]] = None,
        credentials_file: Optional[str] = None,
        dry_run: bool = False
    ) -> PSRemotingResult:
        """
        Revert PS remoting configuration on a server.
        """
        credentials_payload = self._build_credentials_payload(sql_targets or [], credentials_file)
        return self.connection_manager.revert_server(
            server_name=server_name,
            credentials=credentials_payload,
            dry_run=dry_run
        )

    def _persist_connection_profile(self, profile: ServerConnectionProfile) -> None:
        """
        Persist successful connection profile to database.

        """
        try:
            repository = self.connection_manager.repository
            repository.save_connection_profile(
                self._map_profile_to_connection_profile(profile)
            )
            logger.info("Persisted connection profile for server %s", profile.server_name)
        except Exception as exc:
            logger.warning(
                "Failed to persist connection profile for %s: %s",
                profile.server_name,
                exc
            )

    def _build_credentials_payload(
        self,
        sql_targets: List[SqlTarget],
        credentials_ref: Optional[str]
    ) -> dict:
        """Convert configured credentials to PS remoting credential payload."""
        credential = None

        # Prefer explicit override
        chosen_ref = credentials_ref

        # Then per-target OS credential reference
        if not chosen_ref:
            for target in sql_targets:
                if target.os_credentials_ref:
                    chosen_ref = target.os_credentials_ref
                    break

        # Finally audit config OS credentials
        if not chosen_ref:
            try:
                audit_config = self.config_manager.load_audit_config()
                chosen_ref = audit_config.os_credentials_ref
            except Exception:
                chosen_ref = None

        if chosen_ref:
            ref_name = str(Path(chosen_ref).stem)
            try:
                credential = self.config_manager.get_credential(ref_name)
            except Exception as exc:
                logger.warning("Unable to load credential '%s': %s", ref_name, exc)

        if credential:
            return {
                "windows_credentials": {
                    "domain_admin": {
                        "username": credential.username,
                        "password": credential.get_password()
                    }
                }
            }

        return {"windows_credentials": {}}

    def _save_manual_script(self, server_name: str, scripts: List[str]) -> str:
        """Persist manual setup script to disk and return path."""
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        script_path = output_dir / f"manual_psremoting_setup_{server_name}.ps1"
        combined = "\n\n".join(scripts)
        script_path.write_text(combined, encoding="utf-8")
        return str(script_path)

    @staticmethod
    def _map_profile_to_connection_profile(profile: ServerConnectionProfile):
        """Map domain profile to persistence model."""
        from autodbaudit.infrastructure.psremoting.models import (
            ConnectionProfile,
            ConnectionMethod as InfraConnectionMethod
        )

        return ConnectionProfile(
            id=None,
            server_name=profile.server_name,
            connection_method=InfraConnectionMethod.POWERSHELL_REMOTING,
            auth_method=profile.auth_method,
            protocol="http",
            port=profile.port,
            credential_type=None,
            successful=profile.successful,
            last_successful_attempt=profile.last_successful.isoformat(),
            last_attempt=profile.last_successful.isoformat(),
            attempt_count=1,
            sql_targets=profile.sql_targets,
            baseline_state=None,
            current_state=None,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )

    @staticmethod
    def _map_method(method) -> ConnectionMethod:
        """Map infra ConnectionMethod to domain enum."""
        try:
            return ConnectionMethod(method.value)  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            try:
                return ConnectionMethod(str(method))
            except Exception:
                return ConnectionMethod.POWERSHELL_REMOTING
