"""
Audit Data Collection Orchestrator.
Orchestrates specialized collectors to gather audit data.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from autodbaudit.application.collectors.base import CollectorContext
from autodbaudit.application.collectors.server_properties import (
    ServerPropertiesCollector,
)
from autodbaudit.application.collectors.access_control import AccessControlCollector
from autodbaudit.application.collectors.configuration import ConfigurationCollector
from autodbaudit.application.collectors.databases import DatabaseCollector
from autodbaudit.application.collectors.infrastructure import InfrastructureCollector
from autodbaudit.application.collectors.security_policy import SecurityPolicyCollector

if TYPE_CHECKING:
    from autodbaudit.infrastructure.sql.connector import SqlConnector
    from autodbaudit.infrastructure.sql.query_provider import QueryProvider
    from autodbaudit.infrastructure.excel import EnhancedReportWriter

logger = logging.getLogger(__name__)


class AuditDataCollector:
    """
    Orchestrator for all audit data collection.

    Delegates actual collection to specialized collectors.
    Previously known as the monolithic DataCollector.
    """

    def __init__(
        self,
        connector: SqlConnector,
        query_provider: QueryProvider,
        writer: EnhancedReportWriter,
        db_conn=None,
        audit_run_id: int | None = None,
        instance_id: int | None = None,
        expected_builds: dict[str, str] | None = None,
    ) -> None:
        """
        Initialize the orchestrator.
        """
        self.conn = connector
        self.prov = query_provider
        self.writer = writer
        self.db_conn = db_conn
        self.audit_run_id = audit_run_id
        self.instance_id = instance_id
        self.expected_builds = expected_builds or {}

    def collect_all(
        self,
        server_name: str,
        instance_name: str,
        config_name: str = "",
        ip_address: str = "",
    ) -> dict[str, Any]:
        """
        Collect all audit data for an instance.
        """
        # 1. Create Context
        context = CollectorContext(
            connector=self.conn,
            query_provider=self.prov,
            writer=self.writer,
            db_conn=self.db_conn,
            audit_run_id=self.audit_run_id,
            instance_id=self.instance_id,
            expected_builds=self.expected_builds,
            server_name=server_name,
            instance_name=instance_name,
        )

        counts = {}

        # 2. Instantiate and run collectors

        # Instance Properties
        prop_collector = ServerPropertiesCollector(context)
        counts["instances"] = prop_collector.collect(config_name, ip_address)

        # Access Control (Logins, Roles, SA)
        access_collector = AccessControlCollector(context)
        access_counts = access_collector.collect()
        counts.update(access_counts)

        # Configuration (sp_configure)
        config_collector = ConfigurationCollector(context)
        counts["config"] = config_collector.collect()

        # Infrastructure (Services, Protocols, Linked, Backups)
        infra_collector = InfrastructureCollector(context)
        infra_counts = infra_collector.collect()
        counts.update(infra_counts)

        # Databases (DBs, Users, Roles, Triggers, Permissions)
        db_collector = DatabaseCollector(context)
        db_counts = db_collector.collect()
        counts.update(db_counts)

        # Security Policy (Audit, Encryption)
        sec_collector = SecurityPolicyCollector(context)
        sec_counts = sec_collector.collect()
        counts.update(sec_counts)

        return counts
