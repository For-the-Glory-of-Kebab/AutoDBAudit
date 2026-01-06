"""
Configuration manager for the application layer.

This module provides the application layer interface for configuration operations.
It orchestrates domain models and infrastructure components.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from autodbaudit.domain.config import (
    AuditConfig,
    Credential,
    SqlTarget,
    SqlTargets
)
from autodbaudit.infrastructure.config.repository import ConfigRepository

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Application layer manager for configuration operations.

    Provides high-level operations for loading, validating, and managing
    all configuration aspects of the application.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the config manager.

        Args:
            config_dir: Base directory for configuration files.
                       Defaults to 'config' subdirectory of current working directory.
        """
        if config_dir is None:
            config_dir = Path.cwd() / "config"

        self.config_dir = config_dir
        self.repository = ConfigRepository(config_dir)
        self._audit_config: Optional[AuditConfig] = None
        self._sql_targets: Optional[SqlTargets] = None
        self._credentials_cache: Dict[str, Credential] = {}

    def load_audit_config(self, force_reload: bool = False) -> AuditConfig:
        """
        Load audit configuration.

        Args:
            force_reload: Whether to force reload from disk

        Returns:
            AuditConfig domain model

        Raises:
            ValueError: If config cannot be loaded
        """
        if self._audit_config is None or force_reload:
            logger.info("Loading audit configuration")
            self._audit_config = self.repository.load_audit_config()
            logger.info("Loaded audit config for organization: %s", self._audit_config.organization)

        return self._audit_config

    def load_sql_targets(self, force_reload: bool = False) -> SqlTargets:
        """
        Load SQL targets configuration.

        Args:
            force_reload: Whether to force reload from disk

        Returns:
            List of SqlTarget domain models

        Raises:
            ValueError: If config cannot be loaded
        """
        if self._sql_targets is None or force_reload:
            logger.info("Loading SQL targets configuration")
            self._sql_targets = self.repository.load_sql_targets()
            logger.info("Loaded %d SQL targets", len(self._sql_targets))

        return self._sql_targets

    def get_credential(self, cred_ref: str, use_cache: bool = True) -> Credential:
        """
        Get a credential by reference.

        Args:
            cred_ref: Reference name for the credential
            use_cache: Whether to use cached credentials

        Returns:
            Credential domain model

        Raises:
            ValueError: If credential cannot be loaded
        """
        if not use_cache or cred_ref not in self._credentials_cache:
            logger.debug("Loading credential: %s", cred_ref)
            credential = self.repository.load_credential(cred_ref)
            if use_cache:
                self._credentials_cache[cred_ref] = credential
            else:
                return credential

        return self._credentials_cache[cred_ref]

    def get_enabled_targets(self) -> SqlTargets:
        """
        Get all enabled SQL targets.

        Returns:
            List of enabled SqlTarget domain models
        """
        targets = self.load_sql_targets()
        return [target for target in targets if target.enabled]

    def get_targets_by_tag(self, tag: str) -> SqlTargets:
        """
        Get SQL targets filtered by tag.

        Args:
            tag: Tag to filter by

        Returns:
            List of SqlTarget domain models with the specified tag
        """
        targets = self.load_sql_targets()
        return [target for target in targets if tag in target.tags]

    def validate_all_configs(self) -> List[str]:
        """
        Validate all configuration files.

        Returns:
            List of validation error messages (empty if all valid)
        """
        errors = []

        try:
            self.load_audit_config(force_reload=True)
        except Exception as e:
            errors.append(f"Audit config validation failed: {e}")

        try:
            targets = self.load_sql_targets(force_reload=True)
        except Exception as e:
            errors.append(f"SQL targets validation failed: {e}")
            return errors  # Can't validate credentials without targets

        # Validate credentials for each target
        for target in targets:
            try:
                if target.credentials_ref:
                    self.get_credential(target.credentials_ref, use_cache=False)
            except Exception as e:
                errors.append(f"Credential validation failed for target '{target.name}': {e}")

        return errors

    def get_connection_info_for_target(self, target_name: str) -> Optional[SqlTarget]:
        """
        Get connection information for a specific target.

        Args:
            target_name: Name of the target

        Returns:
            SqlTarget if found, None otherwise
        """
        targets = self.load_sql_targets()
        return next((t for t in targets if t.name == target_name), None)

    def clear_cache(self) -> None:
        """Clear all cached configuration data."""
        self._audit_config = None
        self._sql_targets = None
        self._credentials_cache.clear()
        logger.info("Configuration cache cleared")

    def get_config_summary(self) -> Dict[str, any]:
        """
        Get a summary of current configuration state.

        Returns:
            Dictionary with configuration summary
        """
        summary = {
            "config_directory": str(self.config_dir),
            "audit_config_loaded": self._audit_config is not None,
            "sql_targets_loaded": self._sql_targets is not None,
            "cached_credentials": len(self._credentials_cache)
        }

        if self._audit_config:
            summary.update({
                "organization": self._audit_config.organization,
                "audit_year": self._audit_config.audit_year
            })

        if self._sql_targets:
            summary.update({
                "total_targets": len(self._sql_targets),
                "enabled_targets": len(self.get_enabled_targets())
            })

        return summary
