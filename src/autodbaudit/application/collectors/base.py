"""
Base classes and context for audit data collectors.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from autodbaudit.infrastructure.sql.connector import SqlConnector
    from autodbaudit.infrastructure.sql.query_provider import QueryProvider
    from autodbaudit.infrastructure.excel import EnhancedReportWriter

logger = logging.getLogger(__name__)


@dataclass
class CollectorContext:
    """
    Shared context/state for all collectors.
    Propagated through the collector hierarchy.
    """

    connector: SqlConnector
    query_provider: QueryProvider
    writer: EnhancedReportWriter
    server_name: str
    instance_name: str

    # SQLite persistence (Optional)
    db_conn: Any = None  # sqlite3.Connection
    audit_run_id: int | None = None
    instance_id: int | None = None

    # Metadata
    expected_builds: dict[str, str] | None = None


class BaseCollector(ABC):
    """
    Abstract Base Class for specific domain collectors.
    """

    def __init__(self, context: CollectorContext) -> None:
        self.ctx = context
        self.conn = context.connector
        self.prov = context.query_provider
        self.writer = context.writer

    @abstractmethod
    def collect(self) -> Any:
        """
        Execute collection logic.
        """
        pass

    def save_finding(
        self,
        finding_type: str,
        entity_name: str,
        status: str,
        risk_level: str | None = None,
        description: str | None = None,
        recommendation: str | None = None,
        details: str | None = None,
    ) -> None:
        """
        Save a finding to SQLite if db_conn is available in context.
        """
        if self.ctx.db_conn is None or self.ctx.audit_run_id is None:
            return

        try:
            from autodbaudit.infrastructure.sqlite.schema import (
                save_finding,
                build_entity_key,
            )

            entity_key = build_entity_key(
                self.ctx.server_name, self.ctx.instance_name or "(Default)", entity_name
            )

            save_finding(
                connection=self.ctx.db_conn,
                audit_run_id=self.ctx.audit_run_id,
                instance_id=self.ctx.instance_id,
                entity_key=entity_key,
                finding_type=finding_type,
                entity_name=entity_name,
                status=status,
                risk_level=risk_level,
                finding_description=description,
                recommendation=recommendation,
                details=details,
            )
        except Exception as e:
            logger.warning("Failed to save finding '%s': %s", entity_name, e)
