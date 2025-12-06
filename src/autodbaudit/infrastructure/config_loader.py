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
    credential_file: str | None = None
    connect_timeout: int = 30
    tags: List[str] = field(default_factory=list)
    
    @property
    def display_name(self) -> str:
        """Human-readable server name."""
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
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        targets = []
        for item in data.get("targets", []):
            target = SqlTarget(
                id=item["id"],
                server=item["server"],
                instance=item.get("instance"),
                port=item.get("port"),
                auth=item.get("auth", "integrated"),
                username=item.get("username"),
                credential_file=item.get("credential_file"),
                connect_timeout=item.get("connect_timeout", 30),
                tags=item.get("tags", [])
            )
            targets.append(target)
            logger.debug("Loaded target: %s", target.display_name)
        
        logger.info("Loaded %d SQL Server targets", len(targets))
        return targets
    
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
