"""
Main audit service - orchestrates the complete audit workflow.

Phase 1: Instance inventory (connect → detect version → record → Excel)
Future phases add requirement evaluation, remediation, etc.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from autodbaudit.infrastructure.config_loader import ConfigLoader, SqlTarget
from autodbaudit.infrastructure.sql.connector import SqlConnector
from autodbaudit.infrastructure.sql.query_provider import get_query_provider
from autodbaudit.infrastructure.excel import EnhancedReportWriter
from autodbaudit.application.data_collector import AuditDataCollector

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AuditService:
    """
    Main audit engine orchestrator.
    
    Manages the audit workflow:
    1. Load configuration
    2. Connect to SQL targets
    3. Detect versions
    4. Collect all audit data
    5. Generate Excel report
    
    Usage:
        service = AuditService(
            config_dir=Path("config"),
            output_dir=Path("output")
        )
        
        report_path = service.run_audit(
            targets_file="sql_targets.json"
        )
    """
    
    def __init__(
        self,
        config_dir: Path | str = "config",
        output_dir: Path | str = "output"
    ) -> None:
        """
        Initialize audit service.
        
        Args:
            config_dir: Directory containing configuration files
            output_dir: Directory for output files (Excel, scripts, etc.)
        """
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_loader = ConfigLoader(str(self.config_dir))
        
        logger.info("AuditService initialized")
    
    def run_audit(
        self,
        targets_file: str = "sql_targets.json",
        organization: str | None = None
    ) -> Path:
        """
        Run the audit workflow.
        
        Args:
            targets_file: SQL targets configuration filename
            organization: Optional organization name for report
            
        Returns:
            Path to generated Excel report
            
        Raises:
            RuntimeError: If audit fails completely
        """
        logger.info("=" * 60)
        logger.info("Starting SQL Server Audit")
        logger.info("=" * 60)
        
        # Create Excel writer
        writer = EnhancedReportWriter()
        writer.set_audit_info(
            run_id=1,
            organization=organization or "Security Audit",
            started_at=datetime.now(),
        )
        
        success_count = 0
        error_count = 0
        
        try:
            # Load SQL targets
            targets = self.config_loader.load_sql_targets(targets_file)
            logger.info("Loaded %d SQL targets from %s", len(targets), targets_file)
            
            # Process each target
            for target in targets:
                if not target.enabled:
                    logger.info("Skipping disabled target: %s", target.display_name)
                    continue
                    
                try:
                    self._process_target(target, writer)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(
                        "Failed to process target %s: %s",
                        target.display_name, e
                    )
                    # Continue with other targets
            
            # Generate report
            report_path = self._save_report(writer)
            
            logger.info("=" * 60)
            logger.info("Audit completed: %d succeeded, %d failed", success_count, error_count)
            logger.info("Report: %s", report_path)
            logger.info("=" * 60)
            
            return report_path
            
        except Exception as e:
            logger.exception("Audit failed with fatal error: %s", e)
            raise RuntimeError(f"Audit failed: {e}") from e
    
    def _process_target(self, target: SqlTarget, writer: EnhancedReportWriter) -> None:
        """
        Process a single SQL target.
        
        Connects, detects version, collects all audit data.
        
        Args:
            target: SQL target configuration
            writer: Excel report writer
        """
        logger.info("Processing target: %s", target.display_name)
        
        # Create connector
        connector = SqlConnector(
            server_instance=target.server_instance,
            auth=target.auth,
            username=target.username,
            password=target.password,
            connect_timeout=target.connect_timeout
        )
        
        # Test connection
        if not connector.test_connection():
            raise ConnectionError(f"Cannot connect to {target.display_name}")
        
        # Detect version and get query provider
        version_info = connector.detect_version()
        logger.info(
            "Detected: %s version %s (%s)",
            target.display_name, version_info.version, version_info.edition
        )
        
        query_provider = get_query_provider(version_info.version_major)
        
        # Create collector and collect all data
        collector = AuditDataCollector(connector, query_provider, writer)
        counts = collector.collect_all(
            server_name=target.server,
            instance_name=target.instance,
            config_name=target.display_name,
            ip_address=target.ip_address or "",
        )
        
        logger.info(
            "Collected: %d logins, %d roles, %d dbs, %d services",
            counts.get("logins", 0),
            counts.get("roles", 0),
            counts.get("databases", 0),
            counts.get("services", 0),
        )
    
    def _save_report(self, writer: EnhancedReportWriter) -> Path:
        """
        Save Excel report.
        
        Args:
            writer: Populated Excel report writer
            
        Returns:
            Path to generated Excel file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sql_audit_{timestamp}.xlsx"
        output_path = self.output_dir / filename
        
        writer.save(output_path)
        return output_path


# Alias for backwards compatibility
AuditEngine = AuditService
