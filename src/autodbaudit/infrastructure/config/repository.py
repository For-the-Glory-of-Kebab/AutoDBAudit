"""
Configuration repository for loading and saving config files.

This module provides the infrastructure layer for configuration persistence.
It handles file I/O operations and basic validation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

from autodbaudit.domain.config import AuditConfig, Credential, SqlTarget, SqlTargets

# Simple JSONC (JSON with comments) support
def _strip_comments(jsonc_content: str) -> str:
    """Strip comments from JSONC content."""
    # For now, just return the content as-is since we mainly support regular JSON
    # TODO: Implement proper JSONC parsing if needed
    return jsonc_content

logger = logging.getLogger(__name__)


class ConfigRepository:
    """
    Repository for configuration file operations.

    Handles loading and saving of configuration files with support for
    JSON and JSONC formats.
    """

    def __init__(self, config_dir: Path):
        """
        Initialize the config repository.

        Args:
            config_dir: Base directory for configuration files
        """
        self.config_dir = config_dir
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Ensure the configuration directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load_json_file(self, filename: str, allow_jsonc: bool = True) -> Dict[str, Any]:
        """
        Load a JSON or JSONC file.

        Args:
            filename: Name of the file to load (without extension)
            allow_jsonc: Whether to try JSONC if JSON fails

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file cannot be parsed
        """
        json_path = self.config_dir / f"{filename}.json"
        jsonc_path = self.config_dir / f"{filename}.jsonc"

        # Try JSON first
        if json_path.exists():
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse JSON file %s: %s", json_path, e)
                if not allow_jsonc:
                    raise ValueError(f"Invalid JSON in {json_path}") from e

        # Try JSONC if JSON failed or doesn't exist
        if allow_jsonc and jsonc_path.exists():
            try:
                with open(jsonc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    stripped_content = _strip_comments(content)
                    return json.loads(stripped_content)
            except Exception as e:
                logger.error("Failed to parse JSONC file %s: %s", jsonc_path, e)
                raise ValueError(f"Invalid JSONC in {jsonc_path}") from e

        # File not found
        available_files = []
        if json_path.exists():
            available_files.append(str(json_path))
        if jsonc_path.exists():
            available_files.append(str(jsonc_path))

        if available_files:
            files_str = ", ".join(available_files)
            raise FileNotFoundError(f"Could not parse config file '{filename}'. Tried: {files_str}")
        raise FileNotFoundError(
            f"Config file '{filename}.json' or '{filename}.jsonc' not found in {self.config_dir}"
        )

    def save_json_file(self, filename: str, data: Dict[str, Any], use_jsonc: bool = False) -> None:
        """
        Save data to a JSON or JSONC file.

        Args:
            filename: Name of the file to save (without extension)
            data: Data to save
            use_jsonc: Whether to save as JSONC (with comments)
        """
        if use_jsonc:
            filepath = self.config_dir / f"{filename}.jsonc"
            # For JSONC, we'd need to preserve comments, but for now we'll save as regular JSON
            # TODO: Implement proper JSONC saving with comment preservation
            content = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            filepath = self.config_dir / f"{filename}.json"
            content = json.dumps(data, indent=2, ensure_ascii=False)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info("Saved config file: %s", filepath)

    def load_audit_config(self) -> AuditConfig:
        """
        Load audit configuration.

        Returns:
            Parsed AuditConfig domain model

        Raises:
            ValueError: If config cannot be loaded or validated
        """
        try:
            data = self.load_json_file("audit_config")
            return AuditConfig(**data)
        except Exception as e:
            logger.error("Failed to load audit config: %s", e)
            raise ValueError(f"Invalid audit configuration: {e}") from e

    def load_sql_targets(self) -> SqlTargets:
        """
        Load SQL targets configuration.

        Returns:
            List of parsed SqlTarget domain models

        Raises:
            ValueError: If config cannot be loaded or validated
        """
        try:
            data = self.load_json_file("sql_targets")
            targets_data = data.get("targets", data)  # Support both formats

            if not isinstance(targets_data, list):
                raise ValueError("sql_targets must contain a 'targets' array or be an array")

            targets = []
            for i, target_data in enumerate(targets_data):
                try:
                    # Handle backward compatibility for field name changes
                    target_data = self._migrate_target_fields(target_data)
                    target = SqlTarget(**target_data)
                    targets.append(target)
                except Exception as e:
                    logger.error("Invalid target at index %d: %s", i, e)
                    raise ValueError(f"Invalid SQL target at index {i}: {e}") from e

            return targets
        except Exception as e:
            logger.error("Failed to load SQL targets: %s", e)
            raise ValueError(f"Invalid SQL targets configuration: {e}") from e

    def _migrate_target_fields(self, target_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Migrate old field names to new field names for backward compatibility.

        Args:
            target_data: Raw target data from config file

        Returns:
            Migrated target data with new field names
        """
        migrated = target_data.copy()

        # Migrate 'auth' to 'auth_type'
        if 'auth' in migrated and 'auth_type' not in migrated:
            migrated['auth_type'] = migrated.pop('auth')

        # Migrate 'credential_file' to 'credentials_ref'
        if 'credential_file' in migrated and 'credentials_ref' not in migrated:
            # Extract just the filename without path for credentials_ref
            cred_file = migrated.pop('credential_file')
            if cred_file:
                # Remove 'credentials/' prefix if present
                cred_ref = cred_file.replace('credentials/', '').replace('.json', '')
                migrated['credentials_ref'] = cred_ref

        # Set default database if not present
        if 'database' not in migrated:
            migrated['database'] = None

        # Set default description if not present
        if 'description' not in migrated:
            migrated['description'] = None

        return migrated

    def load_credential(self, cred_ref: str) -> Credential:
        """
        Load a specific credential file.

        Args:
            cred_ref: Reference name for the credential file

        Returns:
            Parsed Credential domain model

        Raises:
            ValueError: If credential cannot be loaded or validated
        """
        try:
            # Try multiple locations for backward compatibility
            search_paths = [
                self.config_dir / "credentials" / f"{cred_ref}.json",  # config/credentials/
                self.config_dir.parent / "credentials" / f"{cred_ref}.json",  # root/credentials/
            ]

            cred_data = None
            loaded_path = None
            for path in search_paths:
                if path.exists():
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            cred_data = json.load(f)
                        loaded_path = path
                        break
                    except json.JSONDecodeError as e:
                        logger.warning("Failed to parse credential file %s: %s", path, e)
                        continue

            if cred_data is None:
                raise FileNotFoundError(
                    f"Credential file '{cred_ref}' not found in any expected location"
                )

            logger.debug("Loaded credential from %s", loaded_path)

            # Support both formats: direct object or wrapped in "credentials"
            if "credentials" in cred_data:
                cred_data = cred_data["credentials"]

            return Credential(**cred_data)
        except Exception as e:
            logger.error("Failed to load credential '%s': %s", cred_ref, e)
            raise ValueError(f"Invalid credential '{cred_ref}': {e}") from e

    def list_available_configs(self) -> Dict[str, list]:
        """
        List all available configuration files.

        Returns:
            Dictionary with file categories and their available files
        """
        configs = {
            "audit_configs": [],
            "target_configs": [],
            "credential_files": []
        }

        # Check for audit configs
        for ext in [".json", ".jsonc"]:
            audit_path = self.config_dir / f"audit_config{ext}"
            if audit_path.exists():
                configs["audit_configs"].append(f"audit_config{ext}")

        # Check for target configs
        for ext in [".json", ".jsonc"]:
            targets_path = self.config_dir / f"sql_targets{ext}"
            if targets_path.exists():
                configs["target_configs"].append(f"sql_targets{ext}")

        # Check for credential files
        cred_dir = self.config_dir / "credentials"
        if cred_dir.exists():
            for cred_file in cred_dir.glob("*.json"):
                configs["credential_files"].append(cred_file.name)

        return configs
