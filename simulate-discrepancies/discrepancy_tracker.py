"""
Discrepancy Tracker - Tracks expected discrepancies from simulation scripts.

The simulation SQL scripts create deterministic discrepancies with a @Tag identifier.
This module captures which discrepancies were created and their expected locations
in the audit report.

Key discrepancies created by simulation scripts:
1. SA Account - sa enabled (should be disabled)
2. Configuration - xp_cmdshell, Ad Hoc Distributed Queries, Database Mail XPs enabled
3. Logins - WeakPolicyAdmin_*, UnusedLogin_*, OverprivilegedUser_*, RecentSecurityChange_*
4. Permissions - CONTROL SERVER grants, db_owner escalation
5. Linked Servers - UNAPPROVED_LINK_*, INSECURE_LINK_*
6. Triggers - TR_Unreviewed_Server_*, TR_Unreviewed_DB_*
7. Databases - LegacyTestDB_*, TestDB_*, guest enabled
8. Orphaned Users - OrphanUser_*
9. Certificates - TestCert_* (not backed up)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime


@dataclass
class ExpectedDiscrepancy:
    """A single expected discrepancy to verify."""

    sheet: str
    entity_pattern: str  # Regex pattern to match entity
    column: str  # Column to check
    expected_result: str  # PASS/FAIL/WARN
    description: str


@dataclass
class SimulationRun:
    """Tracks a single simulation run."""

    run_id: str
    tag: str  # The @Tag from SQL script
    timestamp: datetime
    server: str
    instance: str
    sql_version: str

    # Expected discrepancies
    discrepancies: list[ExpectedDiscrepancy] = field(default_factory=list)

    def add_discrepancy(
        self,
        sheet: str,
        entity_pattern: str,
        column: str = "Result",
        expected_result: str = "FAIL",
        description: str = "",
    ) -> None:
        """Add expected discrepancy."""
        self.discrepancies.append(
            ExpectedDiscrepancy(
                sheet=sheet,
                entity_pattern=entity_pattern,
                column=column,
                expected_result=expected_result,
                description=description,
            )
        )

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "run_id": self.run_id,
            "tag": self.tag,
            "timestamp": self.timestamp.isoformat(),
            "server": self.server,
            "instance": self.instance,
            "sql_version": self.sql_version,
            "discrepancies": [
                {
                    "sheet": d.sheet,
                    "entity_pattern": d.entity_pattern,
                    "column": d.column,
                    "expected_result": d.expected_result,
                    "description": d.description,
                }
                for d in self.discrepancies
            ],
        }


def create_expected_discrepancies(tag: str) -> list[ExpectedDiscrepancy]:
    """
    Create list of expected discrepancies for a given tag.

    These match what the simulation SQL scripts create.
    """
    discrepancies = []

    # ═══════════════════════════════════════════════════════════════════
    # SA Account Sheet
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="SA Account",
            entity_pattern="sa",
            column="Result",
            expected_result="FAIL",
            description="SA login enabled (should be disabled)",
        )
    )

    # ═══════════════════════════════════════════════════════════════════
    # Configuration Sheet
    # ═══════════════════════════════════════════════════════════════════
    for config in [
        "xp_cmdshell",
        "Ad Hoc Distributed Queries",
        "Database Mail XPs",
        "remote access",
    ]:
        discrepancies.append(
            ExpectedDiscrepancy(
                sheet="Configuration",
                entity_pattern=re.escape(config),
                column="Result",
                expected_result="FAIL",
                description=f"{config} enabled (security risk)",
            )
        )

    # ═══════════════════════════════════════════════════════════════════
    # Logins Sheet
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Logins",
            entity_pattern=f"WeakPolicyAdmin_{tag}",
            column="Result",
            expected_result="FAIL",
            description="Weak password policy login with sysadmin",
        )
    )

    # Unused logins (1-3 created)
    for i in range(1, 4):
        discrepancies.append(
            ExpectedDiscrepancy(
                sheet="Logins",
                entity_pattern=f"UnusedLogin_{tag}_{i:02d}",
                column="Result",
                expected_result="WARN",
                description=f"Unused login #{i}",
            )
        )

    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Logins",
            entity_pattern=f"OverprivilegedUser_{tag}",
            column="Result",
            expected_result="FAIL",
            description="Overprivileged login in multiple server roles",
        )
    )

    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Logins",
            entity_pattern=f"ComplexSecurityUser_{tag}",
            column="Result",
            expected_result="FAIL",
            description="Login with CONTROL SERVER grant",
        )
    )

    # ═══════════════════════════════════════════════════════════════════
    # Roles Sheet (server roles)
    # ═══════════════════════════════════════════════════════════════════
    for role in ["securityadmin", "serveradmin", "bulkadmin"]:
        discrepancies.append(
            ExpectedDiscrepancy(
                sheet="Roles",
                entity_pattern=f"OverprivilegedUser_{tag}.*{role}",
                column="Result",
                expected_result="WARN",
                description=f"Overprivileged user in {role}",
            )
        )

    # ═══════════════════════════════════════════════════════════════════
    # Permissions Sheet
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Permissions",
            entity_pattern=f"ComplexSecurityUser_{tag}.*CONTROL SERVER",
            column="Result",
            expected_result="FAIL",
            description="Dangerous CONTROL SERVER permission",
        )
    )

    # ═══════════════════════════════════════════════════════════════════
    # Linked Servers Sheet
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Linked Servers",
            entity_pattern=f"UNAPPROVED_LINK_{tag}",
            column="Result",
            expected_result="WARN",
            description="Unapproved linked server",
        )
    )

    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Linked Servers",
            entity_pattern=f"INSECURE_LINK_{tag}",
            column="Result",
            expected_result="FAIL",
            description="Linked server with sa password mapping",
        )
    )

    # ═══════════════════════════════════════════════════════════════════
    # Triggers Sheet
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Triggers",
            entity_pattern=f"TR_Unreviewed_Server_{tag}",
            column="Result",
            expected_result="WARN",
            description="Unreviewed server trigger",
        )
    )

    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Triggers",
            entity_pattern=f"TR_Unreviewed_DB_{tag}",
            column="Result",
            expected_result="WARN",
            description="Unreviewed database trigger",
        )
    )

    # ═══════════════════════════════════════════════════════════════════
    # Databases Sheet
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Databases",
            entity_pattern=f"TestDB_{tag}",
            column="Result",
            expected_result="WARN",
            description="Test database with guest enabled",
        )
    )

    # ═══════════════════════════════════════════════════════════════════
    # Orphaned Users Sheet
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Orphaned Users",
            entity_pattern=f"OrphanUser_{tag}",
            column="Result",
            expected_result="FAIL",
            description="Orphaned user without login",
        )
    )

    # ═══════════════════════════════════════════════════════════════════
    # Encryption Sheet (certificates)
    # ═══════════════════════════════════════════════════════════════════
    discrepancies.append(
        ExpectedDiscrepancy(
            sheet="Encryption",
            entity_pattern=f"TestCert_{tag}",
            column="Result",
            expected_result="WARN",
            description="Certificate not backed up",
        )
    )

    return discrepancies


class DiscrepancyTracker:
    """
    Tracks simulation runs and their expected discrepancies.

    Persists to JSON for verification after audit runs.
    """

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize tracker."""
        self.storage_path = storage_path or Path("output/simulation_tracking.json")
        self.runs: list[SimulationRun] = []
        self._load()

    def _load(self) -> None:
        """Load from persistent storage."""
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                for run_data in data.get("runs", []):
                    run = SimulationRun(
                        run_id=run_data["run_id"],
                        tag=run_data["tag"],
                        timestamp=datetime.fromisoformat(run_data["timestamp"]),
                        server=run_data["server"],
                        instance=run_data["instance"],
                        sql_version=run_data["sql_version"],
                    )
                    for d in run_data.get("discrepancies", []):
                        run.discrepancies.append(ExpectedDiscrepancy(**d))
                    self.runs.append(run)
            except Exception:
                self.runs = []

    def save(self) -> None:
        """Save to persistent storage."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {"runs": [r.to_dict() for r in self.runs]}
        self.storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def add_run(self, run: SimulationRun) -> None:
        """Add a simulation run."""
        self.runs.append(run)
        self.save()

    def get_latest_run(self, server: str | None = None) -> SimulationRun | None:
        """Get the most recent run, optionally filtered by server."""
        filtered = self.runs
        if server:
            filtered = [r for r in self.runs if server.lower() in r.server.lower()]

        if not filtered:
            return None
        return max(filtered, key=lambda r: r.timestamp)

    def get_all_expected_discrepancies(self) -> list[ExpectedDiscrepancy]:
        """Get all expected discrepancies from all runs."""
        all_discs = []
        for run in self.runs:
            all_discs.extend(run.discrepancies)
        return all_discs

    def clear(self) -> None:
        """Clear all tracked runs."""
        self.runs = []
        self.save()
