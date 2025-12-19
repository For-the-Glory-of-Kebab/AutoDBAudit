"""
Test Scenarios and Cycle Definitions.

IMPORTANT: Finding status (FAIL/PASS) is the audit result and stays as-is.
Exception status is stored separately in review_status column.
Tests should check finding_status (FAIL/PASS) separately from exception state.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExpectedState:
    """Expected state for an entity after a cycle."""

    # Finding status: FAIL, PASS, WARN (the audit result - stored in findings table)
    finding_status: Optional[str] = None
    # Review status: None, "Exception" (stored in annotations table)
    review_status: Optional[str] = None
    # Action log type: EXCEPTION_ADDED, Fixed, Regression, etc.
    action_log_type: Optional[str] = None
    # Excel indicator: '✓' (exception documented) or '⏳' (needs review)
    excel_indicator: Optional[str] = None
    # Has justification text
    has_justification: Optional[bool] = None


@dataclass
class TestCycle:
    """A single step in the E2E lifecycle."""

    name: str
    description: str
    command: str  # "audit" or "sync"

    # Mock Data Config (for Audit)
    data_state: str = "BASELINE"  # BASELINE, FIXED, REGRESSION

    # User Actions (for Sync - Pre-execution)
    # List of (Sheet, Entity, ActionType, Value)
    user_actions: list[tuple[str, str, str, Any]] = field(default_factory=list)

    # Verification Expectations
    # Map of EntityKey -> ExpectedState
    expectations: dict[str, ExpectedState] = field(default_factory=dict)

    # Global expectations
    expect_action_log_count_increase: int = 0


# ENTITY KEYS
ENTITY_FAIL = "Login-Fail"
ENTITY_PASS = "Login-Pass"
ENTITY_ROLE = "Sensitive-Role"

CYCLES = [
    TestCycle(
        name="Cycle 1: Fresh Audit",
        description="Initial scan detecting FAIL rows.",
        command="audit",
        data_state="BASELINE",
        expectations={
            ENTITY_FAIL: ExpectedState(
                finding_status="FAIL", review_status=None, excel_indicator="⏳"
            ),
            ENTITY_PASS: ExpectedState(finding_status="PASS", review_status=None),
            ENTITY_ROLE: ExpectedState(
                finding_status="FAIL", review_status=None, excel_indicator="⏳"
            ),
        },
    ),
    TestCycle(
        name="Cycle 2: Add Exceptions",
        description="User adds justifications/status. Sync runs.",
        command="sync",
        user_actions=[
            ("Server Logins", ENTITY_FAIL, "ADD_JUSTIFICATION", "Ticket-123"),
            # PASS row gets justification -> Note only
            ("Server Logins", ENTITY_PASS, "ADD_JUSTIFICATION", "Just a note"),
            # Role gets Exception status
            ("Sensitive Roles", ENTITY_ROLE, "SET_STATUS", "Exception"),
        ],
        expectations={
            # Finding status stays FAIL, but has Exception review_status
            ENTITY_FAIL: ExpectedState(
                finding_status="FAIL",
                review_status="Exception",
                action_log_type="Exception Documented",
                excel_indicator="✓",
                has_justification=True,
            ),
            # PASS row keeps note but no exception status
            ENTITY_PASS: ExpectedState(
                finding_status="PASS",
                review_status=None,  # Exception not valid on PASS
                action_log_type=None,  # No log for note on PASS
                has_justification=True,
            ),
            # Role gets Exception status
            ENTITY_ROLE: ExpectedState(
                finding_status="FAIL",
                review_status="Exception",
                action_log_type="Exception Documented",
                excel_indicator="✓",
            ),
        },
        expect_action_log_count_increase=2,
    ),
    TestCycle(
        name="Cycle 3: Stability",
        description="Sync again with NO changes. Should be idempotent.",
        command="sync",
        expectations={
            ENTITY_FAIL: ExpectedState(
                finding_status="FAIL",
                review_status="Exception",
                action_log_type=None,  # No NEW log
            ),
            ENTITY_ROLE: ExpectedState(
                finding_status="FAIL",
                review_status="Exception",
                action_log_type=None,
            ),
        },
        expect_action_log_count_increase=0,
    ),
    TestCycle(
        name="Cycle 4: Fix Transition",
        description="Underlying issue is fixed in SQL.",
        command="sync",
        data_state="FIXED",
        expectations={
            ENTITY_FAIL: ExpectedState(
                finding_status="PASS",  # Now fixed
                action_log_type="Fixed",
            ),
            ENTITY_ROLE: ExpectedState(
                finding_status="FAIL",
                review_status="Exception",  # Not fixed
            ),
        },
        expect_action_log_count_increase=1,  # FAIL->Fixed
    ),
    TestCycle(
        name="Cycle 5: Regression",
        description="Issue returns. Should auto-recover exception via justification.",
        command="sync",
        data_state="REGRESSION",  # FAIL returns
        expectations={
            # Regression but justification still present = auto-exception
            ENTITY_FAIL: ExpectedState(
                finding_status="FAIL",
                review_status="Exception",
                action_log_type="Regression",
            ),
            ENTITY_ROLE: ExpectedState(
                finding_status="FAIL",
                review_status="Exception",
            ),
        },
        expect_action_log_count_increase=1,
    ),
    TestCycle(
        name="Cycle 6: Explicit Removal",
        description="User clears justification and status.",
        command="sync",
        user_actions=[
            # Clear BOTH for role to remove exception
            ("Sensitive Roles", ENTITY_ROLE, "CLEAR_ALL", None),
            # Clear justification for PASS row (should be silent)
            ("Server Logins", ENTITY_PASS, "CLEAR_JUSTIFICATION", None),
        ],
        expectations={
            ENTITY_ROLE: ExpectedState(
                finding_status="FAIL",
                review_status=None,  # Cleared
                action_log_type="Exception Removed",
                excel_indicator="⏳",
            ),
            ENTITY_PASS: ExpectedState(
                finding_status="PASS",
                action_log_type=None,
            ),
        },
        expect_action_log_count_increase=1,
    ),
]
