"""
SQL Fixture Registry.

Maps fixture names to expected findings in audit report.
"""

from dataclasses import dataclass


@dataclass
class ExpectedFinding:
    """Expected finding from a fixture."""

    sheet: str
    entity: str
    result: str  # PASS/FAIL/WARN
    description: str


# Registry of all atomic fixtures and their expected findings
FIXTURE_REGISTRY: dict[str, ExpectedFinding] = {
    "sa_enable": ExpectedFinding(
        sheet="SA Account",
        entity="sa",
        result="FAIL",
        description="SA login enabled (should be disabled)",
    ),
    "sa_disable": ExpectedFinding(
        sheet="SA Account",
        entity="sa",
        result="PASS",
        description="SA login disabled (compliant)",
    ),
    "login_weak_create": ExpectedFinding(
        sheet="Logins",
        entity="WeakPolicyAdmin_TEST",
        result="FAIL",
        description="Weak policy login created",
    ),
    "login_weak_drop": ExpectedFinding(
        sheet="Logins",
        entity="WeakPolicyAdmin_TEST",
        result="PASS",
        description="Weak policy login removed",
    ),
    "config_xpcmd_enable": ExpectedFinding(
        sheet="Configuration",
        entity="xp_cmdshell",
        result="FAIL",
        description="xp_cmdshell enabled",
    ),
    "config_xpcmd_disable": ExpectedFinding(
        sheet="Configuration",
        entity="xp_cmdshell",
        result="PASS",
        description="xp_cmdshell disabled",
    ),
}


def get_expected_finding(fixture_name: str) -> ExpectedFinding | None:
    """Get expected finding for a fixture."""
    return FIXTURE_REGISTRY.get(fixture_name)


def get_all_fixtures() -> list[str]:
    """Get list of all fixture names."""
    return list(FIXTURE_REGISTRY.keys())
