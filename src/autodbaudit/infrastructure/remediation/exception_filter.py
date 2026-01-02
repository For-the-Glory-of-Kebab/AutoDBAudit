"""
Exception Filter micro-component.
Filters out exceptionalized findings based on annotations table.
Ultra-granular component (<50 lines) following Railway patterns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

from autodbaudit.infrastructure.remediation.results import (
    FilterResult, ExceptionFiltered, Success, Failure
)

if TYPE_CHECKING:
    from sqlite3 import Connection

@dataclass(frozen=True)
class ExceptionFilter:
    """
    Filters findings based on exception status from annotations table.
    Railway-oriented: returns Success with filtered list or Failure with details.
    """

    def filter_exceptions(
        self,
        findings: list[dict],
        db_connection: Connection,
        audit_run_id: int
    ) -> FilterResult:
        """
        Filter out findings that have valid exceptions.
        Returns Success with filtered findings or Failure with filter details.
        """
        if not findings:
            return Success([])

        try:
            # Get all exception annotations for this audit run
            exceptions = db_connection.execute(
                """
                SELECT entity_key, field_value as justification
                FROM annotations
                WHERE audit_run_id = ?
                AND field_name = 'justification'
                AND status_override = 'exception'
                """,
                (audit_run_id,)
            ).fetchall()

            # Create lookup dict for fast filtering
            exception_lookup = {
                row['entity_key']: row['justification'] for row in exceptions
            }

            # Filter findings
            filtered_findings = []
            exceptionalized = []

            for finding in findings:
                entity_key = finding.get('entity_key')
                if entity_key in exception_lookup:
                    finding_copy = dict(finding)
                    finding_copy['is_exceptionalized'] = True
                    finding_copy['justification'] = exception_lookup[entity_key]
                    exceptionalized.append(finding_copy)
                else:
                    finding_copy = dict(finding)
                    finding_copy['is_exceptionalized'] = False
                    finding_copy['justification'] = None
                    filtered_findings.append(finding_copy)

            # Return filtered results with metadata
            if exceptionalized:
                return Failure(ExceptionFiltered(
                    target_server=findings[0].get('server_name', 'unknown'),
                    target_instance=findings[0].get('instance_name', 'unknown'),
                    filtered_findings=[f.get('entity_name', 'unknown') for f in exceptionalized],
                    total_findings=len(findings),
                    reason="exceptionalized"
                ))

            return Success(filtered_findings)

        except Exception as e:
            server_name = (findings[0].get('server_name', 'unknown')
                          if findings else 'unknown')
            instance_name = (findings[0].get('instance_name', 'unknown')
                            if findings else 'unknown')
            return Failure(ExceptionFiltered(
                target_server=server_name,
                target_instance=instance_name,
                filtered_findings=[],
                total_findings=len(findings),
                reason=f"filter_error: {str(e)}"
            ))
