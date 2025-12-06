"""
Main audit service - orchestrates the complete audit workflow.

Phase 1: Instance inventory (connect → detect version → record → Excel)
Future phases add requirement evaluation, remediation, etc.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from autodbaudit.infrastructure.config_loader import ConfigLoader, SqlTarget
from autodbaudit.infrastructure.sql_server import SqlConnector
from autodbaudit.infrastructure.history_store import HistoryStore
from autodbaudit.infrastructure.excel_report import write_instance_inventory

if TYPE_CHECKING:
    from autodbaudit.domain.models import AuditRun

logger = logging.getLogger(__name__)


class AuditService:
    """
    Main audit engine orchestrator.
    
    Manages the audit workflow:
    1. Load configuration
    2. Connect to SQL targets
    3. Detect versions
    4. Record to SQLite history
    5. Generate Excel report
    
    Usage:
        store = HistoryStore(Path("output/history.db"))
        store.initialize_schema()
        
        service = AuditService(
            history_store=store,
            config_dir=Path("config"),
            output_dir=Path("output")
        )
        
        report_path = service.run_audit(
            config_file="audit_config.json",
            targets_file="sql_targets.json"
        )
    """
    
    def __init__(
        self,
        history_store: HistoryStore,
        config_dir: Path | str = "config",
        output_dir: Path | str = "output"
    ) -> None:
        """
        Initialize audit service.
        
        Args:
            history_store: SQLite history store instance
            config_dir: Directory containing configuration files
            output_dir: Directory for output files (Excel, scripts, etc.)
        """
        self.history_store = history_store
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.config_loader = ConfigLoader(str(self.config_dir))
        
        logger.info("AuditService initialized")
    
    def run_audit(
        self,
        config_file: str = "audit_config.json",
        targets_file: str = "sql_targets.json",
        organization: str | None = None
    ) -> Path:
        """
        Run the audit workflow.
        
        Args:
            config_file: Audit configuration filename
            targets_file: SQL targets configuration filename
            organization: Optional organization name (overrides config)
            
        Returns:
            Path to generated Excel report
            
        Raises:
            RuntimeError: If audit fails completely
        """
        logger.info("=" * 60)
        logger.info("Starting SQL Server Audit")
        logger.info("=" * 60)
        
        # Compute config hash for reproducibility
        config_path = self.config_dir / targets_file
        config_hash = self._compute_file_hash(config_path) if config_path.exists() else None
        
        # Begin audit run
        audit_run = self.history_store.begin_audit_run(
            organization=organization,
            config_hash=config_hash
        )
        
        success_count = 0
        error_count = 0
        
        try:
            # Load SQL targets
            targets = self.config_loader.load_sql_targets(targets_file)
            logger.info("Loaded %d SQL targets from %s", len(targets), targets_file)
            
            # Process each target
            for target in targets:
                try:
                    self._process_target(target, audit_run)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(
                        "Failed to process target %s: %s",
                        target.display_name, e
                    )
                    # Continue with other targets
            
            # Determine final status
            if error_count == 0:
                status = "completed"
            elif success_count > 0:
                status = "partial"  # Some succeeded, some failed
            else:
                status = "failed"
            
            # Complete audit run
            self.history_store.complete_audit_run(audit_run.id, status)
            
            # Generate Excel report
            report_path = self._generate_report(audit_run)
            
            logger.info("=" * 60)
            logger.info("Audit completed: %d succeeded, %d failed", success_count, error_count)
            logger.info("Report: %s", report_path)
            logger.info("=" * 60)
            
            return report_path
            
        except Exception as e:
            # Fatal error - mark run as failed
            logger.exception("Audit failed with fatal error: %s", e)
            self.history_store.complete_audit_run(audit_run.id, "failed")
            raise RuntimeError(f"Audit failed: {e}") from e
    
    def _process_target(self, target: SqlTarget, audit_run: AuditRun) -> None:
        """
        Process a single SQL target.
        
        Connects, detects version, records to history.
        
        Args:
            target: SQL target configuration
            audit_run: Current audit run
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
        
        # Detect version
        info = connector.detect_version()
        logger.info(
            "Detected: %s version %s (%s)",
            target.display_name, info.version, info.edition
        )
        
        # Upsert server
        server = self.history_store.upsert_server(
            hostname=target.server,
            ip_address=None  # TODO: DNS lookup or config
        )
        
        # Upsert instance
        instance = self.history_store.upsert_instance_from_info(server, info)
        
        # Link to audit run
        self.history_store.link_instance_to_run(audit_run.id, instance.id)
        
        logger.info("Recorded instance: %s\\%s", server.hostname, instance.instance_name or "(default)")
    
    def _generate_report(self, audit_run: AuditRun) -> Path:
        """
        Generate Excel report for the audit run.
        
        Args:
            audit_run: Completed audit run
            
        Returns:
            Path to generated Excel file
        """
        # Get instances for this run
        instances = self.history_store.get_instances_for_run(audit_run.id)
        
        # Refresh audit run to get ended_at
        audit_run = self.history_store.get_audit_run(audit_run.id) or audit_run
        
        # Generate filename
        timestamp = audit_run.started_at.strftime("%Y%m%d_%H%M%S") if audit_run.started_at else "unknown"
        filename = f"audit_{audit_run.id}_{timestamp}_inventory.xlsx"
        output_path = self.output_dir / filename
        
        # Write report
        return write_instance_inventory(instances, audit_run, output_path)
    
    @staticmethod
    def _compute_file_hash(filepath: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()[:16]  # First 16 chars for brevity


# Alias for backwards compatibility
AuditEngine = AuditService
