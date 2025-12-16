"""
Main audit service - orchestrates the complete audit workflow.

Phase 1: Instance inventory (connect → detect version → record → Excel)
Phase 2: SQLite persistence (store audit data for history tracking)
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
from autodbaudit.infrastructure.sqlite import HistoryStore
from autodbaudit.infrastructure.sqlite.schema import initialize_schema_v2
from autodbaudit.application.collectors.orchestrator import AuditDataCollector

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
    6. Store data in SQLite for history

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
        self, config_dir: Path | str = "config", output_dir: Path | str = "output"
    ) -> None:
        """
        Initialize audit service.

        Args:
            config_dir: Directory containing configuration files
            output_dir: Directory for output files (Excel, SQLite, etc.)
        """
        self.config_dir = Path(config_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.config_loader = ConfigLoader(str(self.config_dir))

        # SQLite history store (lazy initialized)
        self._history_store: HistoryStore | None = None
        self._audit_run_id: int | None = None

        logger.info("AuditService initialized")

    def _get_history_store(self) -> HistoryStore:
        """Get or create the history store."""
        if self._history_store is None:
            db_path = self.output_dir / "audit_history.db"
            self._history_store = HistoryStore(db_path)
            self._history_store.initialize_schema()
            # Initialize v2 tables (extended schema)
            initialize_schema_v2(self._history_store._get_connection())
        return self._history_store

    def run_audit(
        self,
        targets_file: str = "sql_targets.json",
        organization: str | None = None,
        # Allow external control over saving
        skip_save: bool = False,
        # Allow reusing existing writer (for SyncService injection)
        writer: EnhancedReportWriter | None = None,
    ) -> Path | EnhancedReportWriter:
        """
        Run the audit workflow.

        Refactored to support decoupled collection and reporting.

        Args:
            targets_file: SQL targets configuration filename
            organization: Optional organization name for report
            skip_save: If True, returns populate writer instead of saving file
            writer: Optional existing writer to use

        Returns:
            Path object if saved, or EnhancedReportWriter if skip_save=True
        """
        # Step 1: Perform the scan (collect data)
        # This populates the writer and the database
        writer, run_id, counts = self._perform_audit_scan(
            targets_file, organization, writer
        )

        # Step 2: Save Report (unless skipped)
        if skip_save:
            logger.info("Skipping report save (caller will handle it)")
            return writer

        # Standard flow: Save and return path
        return self._save_report(writer, run_id)

    def _perform_audit_scan(
        self,
        targets_file: str,
        organization: str | None,
        writer: EnhancedReportWriter | None = None,
    ) -> tuple[EnhancedReportWriter, int, dict]:
        """
        Core audit logic: Connects, Scans, Collects.

        Returns:
            (populated_writer, audit_run_id, summary_counts)
        """
        logger.info("=" * 60)
        logger.info("Starting SQL Server Audit Scan")
        logger.info("=" * 60)

        # Try to load audit config for metadata
        try:
            audit_config = self.config_loader.load_audit_config()
            config_org = audit_config.organization
            expected_builds = audit_config.expected_builds
        except Exception:
            config_org = None
            expected_builds = {}

        final_org = organization or config_org or "Security Audit"
        audit_name = "SQL Server Security Audit"

        # Initialize SQLite history store
        store = self._get_history_store()
        audit_run = store.begin_audit_run(organization=final_org)
        self._audit_run_id = audit_run.id

        # Create Excel writer if not provided
        if writer is None:
            writer = EnhancedReportWriter()
            writer.set_audit_info(
                run_id=audit_run.id,
                organization=final_org,
                audit_name=audit_name,
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
                    self._process_target(target, writer, store, expected_builds)
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    logger.error(
                        "Failed to process target %s: %s", target.display_name, e
                    )

            # Mark audit run as complete
            status = "completed" if error_count == 0 else "completed_with_errors"
            store.complete_audit_run(audit_run.id, status)

            summary_counts = {"success": success_count, "error": error_count}

            logger.info(
                "Scan completed: %d succeeded, %d failed", success_count, error_count
            )
            return writer, audit_run.id, summary_counts

        except Exception as e:
            # Mark audit run as failed
            if self._audit_run_id:
                store.complete_audit_run(self._audit_run_id, "failed")
            logger.exception("Audit failed with fatal error: %s", e)
            raise RuntimeError(f"Audit failed: {e}") from e

    def _process_target(
        self,
        target: SqlTarget,
        writer: EnhancedReportWriter,
        store: HistoryStore,
        expected_builds: dict[str, str] | None = None,
    ) -> None:
        """
        Process a single SQL target.

        Connects, detects version, collects all audit data.

        Args:
            target: SQL target configuration
            writer: Excel report writer
            store: SQLite history store
            expected_builds: Dict mapping SQL year to expected version
        """
        logger.info("Processing target: %s", target.display_name)

        # Create connector
        connector = SqlConnector(
            server_instance=target.server_instance,
            auth=target.auth,
            username=target.username,
            password=target.password,
            connect_timeout=target.connect_timeout,
        )

        # Test connection
        if not connector.test_connection():
            raise ConnectionError(f"Cannot connect to {target.display_name}")

        # Detect version and get query provider
        version_info = connector.detect_version()
        logger.info(
            "Detected: %s version %s (%s)",
            target.display_name,
            version_info.version,
            version_info.edition,
        )

        # Store server and instance in SQLite
        # Port is required to distinguish default instances on same host
        # Instance name: prefer detected from SQL Server, fallback to config
        detected_instance = version_info.instance_name or ""
        server = store.upsert_server(
            hostname=target.server, ip_address=target.ip_address
        )
        instance = store.upsert_instance(
            server=server,
            instance_name=detected_instance,  # Use SQL Server's actual instance name
            port=target.port or 1433,
            version=version_info.version,
            version_major=version_info.version_major,
            edition=version_info.edition,
            product_level=version_info.product_level,
        )

        # Link instance to this audit run
        if self._audit_run_id:
            store.link_instance_to_run(self._audit_run_id, instance.id)

        query_provider = get_query_provider(version_info.version_major)

        # Create collector with SQLite connection for findings storage
        collector = AuditDataCollector(
            connector,
            query_provider,
            writer,
            db_conn=store._get_connection(),
            audit_run_id=self._audit_run_id,
            instance_id=instance.id,
            expected_builds=expected_builds or {},
        )
        counts = collector.collect_all(
            server_name=target.server,
            instance_name=target.unique_instance,  # Use port-aware identifier
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

    def _save_report(self, writer: EnhancedReportWriter, run_id: int) -> Path:
        """
        Save Excel report.

        Args:
            writer: Populated Excel report writer
            run_id: Audit run ID for filename

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
