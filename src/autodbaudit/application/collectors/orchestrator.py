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

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
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

    def collect_all(  # pylint: disable=too-many-locals
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
        prop_collector = ServerPropertiesCollector(context)
        counts["instances"] = prop_collector.collect(config_name, ip_address)

        access_collector = AccessControlCollector(context)
        counts.update(access_collector.collect())

        config_collector = ConfigurationCollector(context)
        counts["config"] = config_collector.collect()

        infra_collector = InfrastructureCollector(context)
        counts.update(infra_collector.collect())

        db_collector = DatabaseCollector(context)
        counts.update(db_collector.collect())

        sec_collector = SecurityPolicyCollector(context)
        counts.update(sec_collector.collect())

        return counts
