"""
State Machine for Sync Engine.

This module provides THE authoritative logic for classifying state transitions.
All sync/diff operations MUST use this module to determine what type of
change occurred and how it should be handled.

Architecture Note:
    - Pure domain logic - no I/O, no database calls
    - Single source of truth for transition classification
    - All consumers (CLI, Excel, DB) use this module
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from autodbaudit.domain.change_types import (
    FindingStatus,
    ChangeType,
    ActionStatus,
    RiskLevel,
    TransitionResult,
    ExceptionInfo,
)


# =============================================================================
# Protocols (Interfaces)
# =============================================================================

class ExceptionChecker(Protocol):
    """Protocol for checking if an entity has a valid exception."""
    
    def is_exceptioned(self, entity_key: str) -> bool:
        """Check if entity has a documented exception."""
        ...
    
    def get_exception_info(self, entity_key: str) -> ExceptionInfo | None:
        """Get exception details for an entity."""
        ...


class InstanceValidator(Protocol):
    """Protocol for checking if an instance was successfully scanned."""
    
    def was_scanned(self, server: str, instance: str) -> bool:
        """Check if the server/instance was scanned in current run."""
        ...
    
    def is_valid_key(self, entity_key: str) -> bool:
        """Check if entity key belongs to a scanned instance."""
        ...


# =============================================================================
# State Machine Core
# =============================================================================

def classify_finding_transition(
    old_status: FindingStatus | None,
    new_status: FindingStatus | None,
    old_has_exception: bool = False,
    new_has_exception: bool = False,
    instance_was_scanned: bool = True,
) -> TransitionResult:
    """
    Classify a finding state transition.
    
    This is THE authoritative function for determining what type of change
    occurred to a finding. All sync operations MUST use this function.
    
    Args:
        old_status: Previous finding status (None if didn't exist)
        new_status: Current finding status (None if no longer exists)
        old_has_exception: Whether it had an exception before
        new_has_exception: Whether it has an exception now
        instance_was_scanned: Whether the instance was successfully scanned
        
    Returns:
        TransitionResult with change_type and metadata
        
    Priority Rules (when multiple things apply):
        1. FIXED always wins (clears exceptions)
        2. REGRESSION
        3. EXCEPTION_ADDED
        4. EXCEPTION_REMOVED
        5. STILL_FAILING (no log)
    """
    # === GUARD: Instance not scanned ===
    # If we couldn't reach the instance, we can't determine state
    if not instance_was_scanned:
        if old_status is not None and old_status.is_discrepant():
            # Item existed and was failing - we don't know if fixed
            # DO NOT mark as fixed - that would be a false positive
            return TransitionResult(
                change_type=ChangeType.UNKNOWN,
                should_log=False,
                description="Instance unavailable - status unknown",
            )
        return TransitionResult(
            change_type=ChangeType.NO_CHANGE,
            should_log=False,
        )
    
    # === CASE: Row didn't exist before ===
    if old_status is None:
        if new_status is not None and new_status.is_discrepant():
            # New discrepancy appeared
            return TransitionResult(
                change_type=ChangeType.NEW_ISSUE,
                should_log=True,
                action_status=ActionStatus.OPEN,
                risk_level=RiskLevel.HIGH,
                description="New issue detected",
            )
        # New PASS or still doesn't exist - no action
        return TransitionResult(
            change_type=ChangeType.NO_CHANGE,
            should_log=False,
        )
    
    # === CASE: Row no longer exists or became PASS ===
    if new_status is None or new_status == FindingStatus.PASS:
        if old_status.is_discrepant():
            # Was failing, now fixed/gone - THIS IS A FIX
            # Note: Fix clears any exception (fix takes precedence)
            return TransitionResult(
                change_type=ChangeType.FIXED,
                should_log=True,
                action_status=ActionStatus.CLOSED,
                risk_level=RiskLevel.LOW,
                description="Issue resolved",
            )
        # Was PASS, still PASS or gone - no change
        return TransitionResult(
            change_type=ChangeType.NO_CHANGE,
            should_log=False,
        )
    
    # === CASE: PASS → FAIL/WARN (Regression) ===
    if old_status == FindingStatus.PASS and new_status.is_discrepant():
        return TransitionResult(
            change_type=ChangeType.REGRESSION,
            should_log=True,
            action_status=ActionStatus.REGRESSION,
            risk_level=RiskLevel.HIGH,
            description="Issue re-appeared (regression)",
        )
    
    # === CASE: Still discrepant (FAIL→FAIL or WARN→WARN) ===
    if old_status.is_discrepant() and new_status.is_discrepant():
        # Check for exception state changes
        if not old_has_exception and new_has_exception:
            # Exception was added
            return TransitionResult(
                change_type=ChangeType.EXCEPTION_ADDED,
                should_log=True,
                action_status=ActionStatus.EXCEPTION,
                risk_level=RiskLevel.INFO,
                description="Exception documented",
            )
        
        if old_has_exception and not new_has_exception:
            # Exception was removed (user cleared justification)
            return TransitionResult(
                change_type=ChangeType.EXCEPTION_REMOVED,
                should_log=True,
                action_status=ActionStatus.PENDING,
                risk_level=RiskLevel.MEDIUM,
                description="Exception removed - needs attention",
            )
        
        # Still failing, no exception change - no log
        return TransitionResult(
            change_type=ChangeType.STILL_FAILING,
            should_log=False,
            action_status=ActionStatus.OPEN,
        )
    
    # === DEFAULT: No change ===
    return TransitionResult(
        change_type=ChangeType.NO_CHANGE,
        should_log=False,
    )


def classify_exception_change(
    old_exception: ExceptionInfo | None,
    new_exception: ExceptionInfo | None,
    current_status: FindingStatus | None,
) -> TransitionResult:
    """
    Classify a change in exception status.
    
    This handles the nuance between "new exception" and "updated exception".
    Important: Updating justification text is NOT a new exception for counting.
    
    Args:
        old_exception: Previous exception info (None if none)
        new_exception: Current exception info (None if none)
        current_status: Current finding status
        
    Returns:
        TransitionResult for the exception change
    """
    # If not discrepant, exception doesn't apply
    if current_status is None or not current_status.is_discrepant():
        if new_exception and new_exception.is_valid:
            # Has exception on non-discrepant - should be cleared
            return TransitionResult(
                change_type=ChangeType.NO_CHANGE,
                should_log=False,
                description="Exception on compliant row (will be cleared)",
            )
        return TransitionResult(
            change_type=ChangeType.NO_CHANGE,
            should_log=False,
        )
    
    old_valid = old_exception.is_valid if old_exception else False
    new_valid = new_exception.is_valid if new_exception else False
    
    # Exception added
    if not old_valid and new_valid:
        return TransitionResult(
            change_type=ChangeType.EXCEPTION_ADDED,
            should_log=True,
            action_status=ActionStatus.EXCEPTION,
            risk_level=RiskLevel.INFO,
            description="Exception documented",
        )
    
    # Exception removed
    if old_valid and not new_valid:
        return TransitionResult(
            change_type=ChangeType.EXCEPTION_REMOVED,
            should_log=True,
            action_status=ActionStatus.PENDING,
            risk_level=RiskLevel.MEDIUM,
            description="Exception removed",
        )
    
    # Exception updated (had one, still has one, but text changed)
    if old_valid and new_valid:
        old_text = old_exception.justification_text if old_exception else None
        new_text = new_exception.justification_text if new_exception else None
        if old_text != new_text:
            return TransitionResult(
                change_type=ChangeType.EXCEPTION_UPDATED,
                should_log=True,  # Log it, but don't increment count
                action_status=ActionStatus.EXCEPTION,
                risk_level=RiskLevel.INFO,
                description="Exception updated",
            )
    
    # No change
    return TransitionResult(
        change_type=ChangeType.NO_CHANGE,
        should_log=False,
    )


def resolve_concurrent_changes(
    changes: list[TransitionResult],
) -> TransitionResult:
    """
    Resolve multiple concurrent changes to the same entity.
    
    When multiple things happen in one sync (e.g., exception added AND fixed),
    the highest priority change wins.
    
    Args:
        changes: List of detected changes for same entity
        
    Returns:
        The winning TransitionResult based on priority
    """
    if not changes:
        return TransitionResult(
            change_type=ChangeType.NO_CHANGE,
            should_log=False,
        )
    
    if len(changes) == 1:
        return changes[0]
    
    # Sort by priority (lower = higher priority)
    sorted_changes = sorted(changes, key=lambda c: c.change_type.priority)
    return sorted_changes[0]


# =============================================================================
# Exception Validity Checks
# =============================================================================

def is_exception_eligible(
    status: FindingStatus | None,
    has_justification: bool,
    review_status: str | None,
) -> bool:
    """
    Check if a row is eligible to be counted as an exception.
    
    Rules:
        1. MUST be discrepant (FAIL or WARN status)
        2. MUST have (justification OR review_status == "Exception")
        
    Args:
        status: Current finding status
        has_justification: Whether justification field has content
        review_status: Value of Review Status dropdown
        
    Returns:
        True if this counts as a documented exception
    """
    # Must be discrepant
    if status is None or not status.is_discrepant():
        return False
    
    # Must have exception documentation
    # Note: review_status may include emoji prefix like "✓ Exception"
    has_exception_status = review_status is not None and "Exception" in str(review_status)
    return has_justification or has_exception_status


def should_clear_exception_status(
    status: FindingStatus | None,
    review_status: str | None,
) -> bool:
    """
    Check if exception status should be cleared on non-discrepant row.
    
    Rule: If row is PASS but has Review Status = "Exception",
          that status should be cleared as it's meaningless.
          
    Note: Justification is NOT cleared (it becomes a note).
    
    Args:
        status: Current finding status
        review_status: Current Review Status dropdown value
        
    Returns:
        True if review_status should be cleared
    """
    if status is None or status == FindingStatus.PASS:
        # Note: review_status may include emoji prefix like "✓ Exception"
        if review_status is not None and "Exception" in str(review_status):
            return True
    return False


# =============================================================================
# Counting Logic
# =============================================================================

def count_active_issues(
    findings: list[dict],
    exception_checker: ExceptionChecker,
) -> int:
    """
    Count active issues (discrepant without exception).
    
    Args:
        findings: List of finding dicts with 'entity_key' and 'status'
        exception_checker: Implementation of ExceptionChecker protocol
        
    Returns:
        Count of active issues requiring attention
    """
    count = 0
    for finding in findings:
        status = FindingStatus.from_string(finding.get("status"))
        if status and status.is_discrepant():
            entity_key = finding.get("entity_key", "")
            if not exception_checker.is_exceptioned(entity_key):
                count += 1
    return count


def count_documented_exceptions(
    findings: list[dict],
    exception_checker: ExceptionChecker,
) -> int:
    """
    Count documented exceptions (discrepant WITH exception).
    
    Args:
        findings: List of finding dicts
        exception_checker: Implementation of ExceptionChecker protocol
        
    Returns:
        Count of documented exceptions
    """
    count = 0
    for finding in findings:
        status = FindingStatus.from_string(finding.get("status"))
        if status and status.is_discrepant():
            entity_key = finding.get("entity_key", "")
            if exception_checker.is_exceptioned(entity_key):
                count += 1
    return count


def count_compliant(findings: list[dict]) -> int:
    """
    Count compliant items (PASS status).
    
    Args:
        findings: List of finding dicts
        
    Returns:
        Count of compliant items
    """
    count = 0
    for finding in findings:
        status = FindingStatus.from_string(finding.get("status"))
        if status == FindingStatus.PASS:
            count += 1
    return count
