"""
Dependency injection container for the application.

This module provides a centralized way to create and manage application dependencies.
It follows the dependency injection pattern for clean architecture.
"""

import logging
from pathlib import Path
from typing import Optional

from ..domain.config.audit_settings import AuditSettings
from ..infrastructure.config.credential_manager import CredentialManager
from ..infrastructure.config.manager import ConfigManager
from ..infrastructure.config.repository import ConfigRepository
from ..infrastructure.sqlite.store import HistoryStore
from .prepare.cache.cache_manager import ConnectionCacheManager
from .prepare.connection.connection_tester import ConnectionTestingService
from .prepare.detection.os_detector import OSDetectionService
from .prepare.method.method_selector import ConnectionMethodSelector
from .prepare_service import PrepareService

logger = logging.getLogger(__name__)


class Container:
    """
    Dependency injection container.

    Manages the creation and lifecycle of application services and infrastructure components.
    """

    def __init__(self, config_dir: Optional[Path] = None, audit_settings: Optional[AuditSettings] = None):
        """
        Initialize the container.

        Args:
            config_dir: Base directory for configuration files
            audit_settings: Dynamic audit settings for timeouts and performance (overrides config file)
        """
        self.config_dir = config_dir or Path.cwd() / "config"
        
        # Load audit settings from config file, or use provided override
        if audit_settings is None:
            try:
                audit_config = self.config_manager.load_audit_config()
                self.audit_settings = audit_config.audit_settings
            except Exception:
                # Fallback to defaults if config loading fails
                self.audit_settings = AuditSettings()
        else:
            self.audit_settings = audit_settings

        self._config_repository: Optional[ConfigRepository] = None
        self._config_manager: Optional[ConfigManager] = None
        self._credential_manager: Optional[CredentialManager] = None
        self._prepare_service: Optional[PrepareService] = None

        # Ultra-granular prepare components
        self._os_detector: Optional[OSDetectionService] = None
        self._connection_tester: Optional[ConnectionTestingService] = None
        self._method_selector: Optional[ConnectionMethodSelector] = None
        self._cache_manager: Optional[ConnectionCacheManager] = None
        self._history_store: Optional[HistoryStore] = None

    @property
    def config_repository(self) -> ConfigRepository:
        """Get the configuration repository."""
        if self._config_repository is None:
            self._config_repository = ConfigRepository(self.config_dir)
        return self._config_repository

    @property
    def config_manager(self) -> ConfigManager:
        """Get the configuration manager."""
        if self._config_manager is None:
            self._config_manager = ConfigManager(self.config_dir)
        return self._config_manager

    @property
    def credential_manager(self) -> CredentialManager:
        """Get the credential manager."""
        if self._credential_manager is None:
            self._credential_manager = CredentialManager(self.config_repository)
        return self._credential_manager

    @property
    def os_detector(self) -> OSDetectionService:
        """Get the OS detection service."""
        if self._os_detector is None:
            self._os_detector = OSDetectionService()
        return self._os_detector

    @property
    def connection_tester(self) -> ConnectionTestingService:
        """Get the connection testing service."""
        if self._connection_tester is None:
            self._connection_tester = ConnectionTestingService()
        return self._connection_tester

    @property
    def method_selector(self) -> ConnectionMethodSelector:
        """Get the connection method selector."""
        if self._method_selector is None:
            self._method_selector = ConnectionMethodSelector()
        return self._method_selector

    @property
    def cache_manager(self) -> ConnectionCacheManager:
        """Get the connection cache manager."""
        if self._cache_manager is None:
            self._cache_manager = ConnectionCacheManager()
        return self._cache_manager

    @property
    def history_store(self) -> HistoryStore:
        """Get the history store for DB persistence."""
        if self._history_store is None:
            # Use output directory for history DB
            output_dir = self.config_dir.parent / "output"
            db_path = output_dir / "audit_history.db"
            self._history_store = HistoryStore(db_path)
        return self._history_store

    @property
    def prepare_service(self) -> PrepareService:
        """Get the prepare service with ultra-granular components."""
        if self._prepare_service is None:
            self._prepare_service = PrepareService(
                config_manager=self.config_manager,
                os_detector=self.os_detector,
                connection_tester=self.connection_tester,
                method_selector=self.method_selector,
                cache_manager=self.cache_manager,
                audit_settings=self.audit_settings,
                history_store=self.history_store,
            )
        return self._prepare_service

    def reload_audit_settings(self) -> None:
        """
        Reload audit settings from config file.
        
        This allows dynamic timeout changes mid-audit.
        """
        try:
            audit_config = self.config_manager.load_audit_config(force_reload=True)
            self.audit_settings = audit_config.audit_settings
            logger.info("Reloaded audit settings from config file")
        except Exception as e:
            logger.warning("Failed to reload audit settings: %s", e)

    def reset(self) -> None:
        """Reset all cached instances."""
        self._config_repository = None
        self._config_manager = None
        self._credential_manager = None
        self._prepare_service = None

        # Reset ultra-granular components
        self._os_detector = None
        self._connection_tester = None
        self._method_selector = None
        self._cache_manager = None
        self._history_store = None

        logger.info("Container reset - all instances cleared")
