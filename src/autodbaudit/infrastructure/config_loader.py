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


class ConfigLoader:
    """
    Load and validate configuration files.
    
    Implements schema validation and provides typed access to configuration data.
    """
    
    def __init__(self, config_dir: str = "config"):
        """
        Initialize config loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        logger.info("ConfigLoader initialized with directory: %s", self.config_dir)
    
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
        
        if not filepath.exists():
            raise FileNotFoundError(f"SQL targets config not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
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
        
        if not path.exists():
            logger.warning("Credential file not found: %s", filepath)
            return {}
        
        logger.debug("Loading credentials from: %s", path)
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
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
        
        if not filepath.exists():
            raise FileNotFoundError(f"Audit config not found: {filepath}")
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        config = AuditConfig(
            organization=data["organization"],
            audit_year=data["audit_year"],
            audit_date=data["audit_date"],
            output_directory=data.get("output", {}).get("directory", "./output"),
            filename_pattern=data.get("output", {}).get("filename_pattern",
                                                        "{organization}_SQL_Audit_{date}.xlsx"),
            include_charts=data.get("output", {}).get("include_charts", True),
            verbosity=data.get("output", {}).get("verbosity", "detailed"),
            minimum_sql_version=data.get("requirements", {}).get("minimum_sql_version", "2019"),
            requirements=data.get("requirements", {})
        )
        
        logger.info(
            "Loaded audit config for: %s (%d)",
            config.organization, config.audit_year
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
