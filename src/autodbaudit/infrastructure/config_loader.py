"""
Configuration loader module.

Handles loading and validation of JSON configuration files:
- sql_targets.json: SQL Server connection configurations
- audit_config.json: Audit settings and requirements
- hotfix_mapping.json: Hotfix version mappings
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class SqlTarget:
    """SQL Server target configuration."""

    id: str
    server: str
    instance: str | None = None
    port: int | None = None
    auth: str = "integrated"  # 'integrated' or 'sql'
    username: str | None = None
    password: str | None = None  # For testing; production should use credential_file
    credential_file: str | None = None
    connect_timeout: int = 30
    tags: List[str] = field(default_factory=list)
    enabled: bool = True  # Whether to include in audit
    ip_address: str | None = None  # Optional IP address override
    name: str | None = None  # Human-readable display name for reports
    os_credential_file: str | None = None  # Separate credential file for OS/PSRemoting
    os_username: str | None = None  # OS username for PSRemoting
    os_password: str | None = None  # OS password for PSRemoting

    @property
    def display_name(self) -> str:
        """Human-readable server name for reports.

        Returns the 'name' field if set, otherwise generates from connection info.
        """
        if self.name:
            return self.name
        if self.port:
            return f"{self.server}:{self.port}"
        elif self.instance:
            return f"{self.server}\\{self.instance}"
        return self.server

    @property
    def unique_instance(self) -> str:
        """Unique instance identifier for entity keys.

        When instance name is null/empty (default instance), uses port for disambiguation.
        This ensures multiple default instances on different ports are distinguishable.

        Returns:
            Instance identifier like "MSSQLSERVER", "SQLEXPRESS", or ":1434" (port-based)
        """
        if self.instance:
            return self.instance
        # Default instance - use port for disambiguation if non-standard
        if self.port and self.port != 1433:
            return f":{self.port}"
        return ""  # Standard default instance on 1433

    @property
    def server_instance(self) -> str:
        """Server instance string for connection."""
        if self.port:
            return f"{self.server},{self.port}"
        elif self.instance:
            return f"{self.server}\\{self.instance}"
        return self.server


@dataclass
class AuditConfig:
    """Audit configuration settings."""

    organization: str
    audit_year: int
    audit_date: str
    output_directory: str = "./output"
    filename_pattern: str = "{organization}_SQL_Audit_{date}.xlsx"
    include_charts: bool = True
    verbosity: str = "detailed"
    minimum_sql_version: str = "2019"
    requirements: Dict[str, Any] = field(default_factory=dict)

    @property
    def expected_builds(self) -> Dict[str, str]:
        """
        Get expected build versions per SQL major version year.

        Returns:
            Dict mapping SQL year ("2022", "2019", etc.) to expected build string.
            Empty dict if not configured (all versions assumed current).
        """
        return self.requirements.get("expected_builds", {})


class ConfigLoader:
    """
    Load and validate configuration files.

    Implements schema validation and provides typed access to configuration data.
    """

    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader.

        Args:
            config_dir: Directory containing configuration files.
                        If "config" (default), attempts to resolve relative to executable location when frozen.
        """
        import sys

        # If running as PyInstaller EXE and using default relative path, anchor it to the EXE location
        if getattr(sys, "frozen", False) and not Path(config_dir).is_absolute():
            base_dir = Path(sys.executable).parent
            self.config_dir = base_dir / config_dir
        else:
            self.config_dir = Path(config_dir)

        logger.info("ConfigLoader initialized with directory: %s", self.config_dir)

    def _load_json_file(self, filepath: Path, required: bool = True) -> dict | None:
        """
        Load and parse a JSON file with robust error handling.

        Provides clear error messages for common failure scenarios:
        - File not found
        - File corrupted (invalid JSON syntax)
        - File empty
        - Permission denied

        Args:
            filepath: Absolute or relative path to JSON file
            required: If True, raises exception on error. If False, returns None.

        Returns:
            Parsed JSON as dict, or None if optional file not found

        Raises:
            FileNotFoundError: If required file doesn't exist
            ValueError: If JSON is malformed or empty
            PermissionError: If file cannot be read
        """
        if not filepath.exists():
            if required:
                raise FileNotFoundError(
                    f"Configuration file not found: {filepath}\n"
                    f"Hint: Copy the .example.json file and customize it."
                )
            logger.debug("Optional config not found: %s", filepath)
            return None

        try:
            content = filepath.read_text(encoding="utf-8")
        except PermissionError as e:
            raise PermissionError(
                f"Cannot read config file (permission denied): {filepath}\n"
                f"Hint: Check file permissions or if another process has it locked."
            ) from e

        if not content.strip():
            raise ValueError(
                f"Configuration file is empty: {filepath}\n"
                f"Hint: Add valid JSON content or copy from .example.json"
            )

        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Invalid JSON in config file: {filepath}\n"
                f"Error at line {e.lineno}, column {e.colno}: {e.msg}\n"
                f"Hint: Validate JSON syntax. Note: .json files cannot have comments."
            ) from e

    def load_sql_targets(self, filename: str = "sql_targets.json") -> List[SqlTarget]:
        """
        Load SQL Server target configurations.

        Args:
            filename: Config file name

        Returns:
            List of SqlTarget objects

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        filepath = self.config_dir / filename
        logger.info("Loading SQL targets from: %s", filepath)

        data = self._load_json_file(filepath, required=True)

        targets = []
        for item in data.get("targets", []):
            # Load credentials from file if specified
            username = item.get("username")
            password = item.get("password")
            credential_file = item.get("credential_file")

            if credential_file and not password:
                creds = self._load_credential_file(credential_file)
                username = creds.get("username", username)
                password = creds.get("password")

            # Load OS credentials from file if specified
            os_credential_file = item.get("os_credential_file")
            os_username = item.get("os_username")
            os_password = item.get("os_password")

            if os_credential_file and not os_password:
                os_creds = self._load_credential_file(os_credential_file)
                os_username = os_creds.get("username", os_username)
                os_password = os_creds.get("password")

            target = SqlTarget(
                id=item["id"],
                server=item["server"],
                instance=item.get("instance"),
                port=item.get("port"),
                auth=item.get("auth", "integrated"),
                username=username,
                password=password,
                credential_file=credential_file,
                connect_timeout=item.get("connect_timeout", 30),
                tags=item.get("tags", []),
                enabled=item.get("enabled", True),
                ip_address=item.get("ip_address"),
                name=item.get("name"),
                os_credential_file=os_credential_file,
                os_username=os_username,
                os_password=os_password,
            )
            targets.append(target)
            logger.debug("Loaded target: %s", target.display_name)

        logger.info("Loaded %d SQL Server targets", len(targets))
        return targets

    def _load_credential_file(self, filepath: str) -> dict:
        """
        Load credentials from a JSON file.

        Args:
            filepath: Path to credential file (relative to project root or absolute)

        Returns:
            Dictionary with 'username' and 'password' keys
        """
        path = Path(filepath)
        if not path.is_absolute():
            # Try relative to project root (parent of config_dir)
            path = self.config_dir.parent / filepath

        logger.debug("Loading credentials from: %s", path)
        data = self._load_json_file(path, required=False)

        if data is None:
            logger.warning("Credential file not found: %s", filepath)
            return {}

        return {
            "username": data.get("username"),
            "password": data.get("password"),
        }

    def load_audit_config(self, filename: str = "audit_config.json") -> AuditConfig:
        """
        Load audit configuration.

        Args:
            filename: Config file name

        Returns:
            AuditConfig object

        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        filepath = self.config_dir / filename
        logger.info("Loading audit config from: %s", filepath)

        data = self._load_json_file(filepath, required=True)

        config = AuditConfig(
            organization=data["organization"],
            audit_year=data["audit_year"],
            audit_date=data["audit_date"],
            output_directory=data.get("output", {}).get("directory", "./output"),
            filename_pattern=data.get("output", {}).get(
                "filename_pattern", "{organization}_SQL_Audit_{date}.xlsx"
            ),
            include_charts=data.get("output", {}).get("include_charts", True),
            verbosity=data.get("output", {}).get("verbosity", "detailed"),
            minimum_sql_version=data.get("requirements", {}).get(
                "minimum_sql_version", "2019"
            ),
            requirements=data.get("requirements", {}),
        )
        # Dynamically attach OS settings not in dataclass yet
        config.os_remediation = data.get("os_remediation", {})

        logger.info(
            "Loaded audit config for: %s (%d)", config.organization, config.audit_year
        )
        return config

    def validate_config(self, config_type: str = "all") -> bool:
        """
        Validate configuration files.

        Args:
            config_type: 'sql_targets', 'audit_config', or 'all'

        Returns:
            True if valid, False otherwise
        """
        try:
            if config_type in ("sql_targets", "all"):
                self.load_sql_targets()
            if config_type in ("audit_config", "all"):
                self.load_audit_config()
            logger.info("Configuration validation passed")
            return True
        except Exception as e:
            logger.error("Configuration validation failed: %s", e)
            return False
