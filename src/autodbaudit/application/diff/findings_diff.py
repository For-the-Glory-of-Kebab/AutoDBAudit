"""
Findings Diff - Pure function for comparing findings between runs.

This module provides diff functionality for compliance findings,
using the domain state machine for transition classification.

Architecture Note:
    - Pure functions with no side effects
    - No database or file I/O
    - Uses domain types and state machine
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from autodbaudit.domain.change_types import (
    FindingStatus,
    ChangeType,
    DetectedChange,
    RiskLevel,
    EntityType,
)
from autodbaudit.domain.state_machine import (
    classify_finding_transition,
)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class FindingsDiffResult:
    """
    Result of diffing two findings lists.
    
    Contains both counts and detailed lists of changes.
    """
    # Counts
    fixed_count: int = 0
    regression_count: int = 0
    new_issue_count: int = 0
    still_failing_count: int = 0
    exception_added_count: int = 0
    exception_removed_count: int = 0
    
    # Detailed changes (for logging)
    fixed: list[DetectedChange] = field(default_factory=list)
    regressions: list[DetectedChange] = field(default_factory=list)
    new_issues: list[DetectedChange] = field(default_factory=list)
    exception_changes: list[DetectedChange] = field(default_factory=list)
    
    @property
    def has_changes(self) -> bool:
        """Check if any changes were detected."""
        return (
            self.fixed_count > 0 or
            self.regression_count > 0 or
            self.new_issue_count > 0 or
            self.exception_added_count > 0 or
            self.exception_removed_count > 0
        )
    
    @property
    def total_changes(self) -> int:
        """Total number of changes."""
        return (
            self.fixed_count +
            self.regression_count +
            self.new_issue_count +
            self.exception_added_count +
            self.exception_removed_count
        )


# =============================================================================
# Helper Functions
# =============================================================================

def build_findings_map(findings: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Build a map of entity_key -> finding dict.
    
    Args:
        findings: List of finding dicts with 'entity_key'
        
    Returns:
        Dict keyed by entity_key
    """
    return {f.get("entity_key", ""): f for f in findings if f.get("entity_key")}


def extract_server_instance(entity_key: str) -> tuple[str, str]:
    """
    Extract server and instance from an entity key.
    
    Keys have format: Type|Server|Instance|... or Server|Instance|...
    
    Args:
        entity_key: The entity key to parse
        
    Returns:
        Tuple of (server, instance)
    """
    parts = entity_key.split("|")
    
    if len(parts) >= 3:
        # Check if first part is a type
        known_types = {"sa_account", "login", "config", "service", "database", 
                       "backup", "trigger", "protocol", "encryption"}
        if parts[0].lower() in known_types:
            return parts[1], parts[2]
    
    if len(parts) >= 2:
        return parts[0], parts[1]
    
    return parts[0] if parts else "", ""


def is_instance_valid(
    entity_key: str,
    valid_instance_keys: set[str],
) -> bool:
    """
    Check if entity belongs to a scanned instance.
    
    Args:
        entity_key: The entity key to check
        valid_instance_keys: Set of "Server|Instance" keys that were scanned
        
    Returns:
        True if instance was scanned (or no validation needed)
    """
    if not valid_instance_keys:
        return True  # No validation = assume valid
    
    server, instance = extract_server_instance(entity_key)
    check_key = f"{server}|{instance}".lower()
    
    return check_key in {k.lower() for k in valid_instance_keys}


def derive_entity_type(entity_key: str) -> EntityType:
    """
    Derive entity type from entity key prefix.
    
    Args:
        entity_key: The entity key to analyze
        
    Returns:
        EntityType enum value
    """
    parts = entity_key.split("|")
    if not parts:
        return EntityType.CONFIGURATION
    
    prefix = parts[0].lower()
    type_map = {
        "sa_account": EntityType.SA_ACCOUNT,
        "login": EntityType.LOGIN,
        "role": EntityType.SERVER_ROLE,
        "config": EntityType.CONFIGURATION,
        "service": EntityType.SERVICE,
        "database": EntityType.DATABASE,
        "db_user": EntityType.DATABASE_USER,
        "db_role": EntityType.DATABASE_ROLE,
        "orphan": EntityType.ORPHANED_USER,
        "linked_server": EntityType.LINKED_SERVER,
        "trigger": EntityType.TRIGGER,
        "backup": EntityType.BACKUP,
        "protocol": EntityType.PROTOCOL,
        "encryption": EntityType.ENCRYPTION,
        "audit": EntityType.AUDIT_SETTING,
        "instance": EntityType.INSTANCE,
    }
    
    return type_map.get(prefix, EntityType.CONFIGURATION)


# =============================================================================
# Main Diff Function
# =============================================================================

def diff_findings(
    old_findings: list[dict[str, Any]],
    new_findings: list[dict[str, Any]],
    old_exceptions: set[str] | None = None,
    new_exceptions: set[str] | None = None,
    valid_instance_keys: set[str] | None = None,
) -> FindingsDiffResult:
    """
    Diff two findings lists and classify all transitions.
    
    This is THE primary diff function for findings comparison.
    Uses the domain state machine for accurate transition classification.
    
    Args:
        old_findings: Previous run's findings
        new_findings: Current run's findings
        old_exceptions: Set of entity keys that were exceptioned before
        new_exceptions: Set of entity keys that are exceptioned now
        valid_instance_keys: Set of "Server|Instance" keys that were scanned
                           (used to avoid false positives when instance unavailable)
    
    Returns:
        FindingsDiffResult with counts and detailed changes
    """
    result = FindingsDiffResult()
    
    old_exceptions = old_exceptions or set()
    new_exceptions = new_exceptions or set()
    valid_instance_keys = valid_instance_keys or set()
    
    old_map = build_findings_map(old_findings)
    new_map = build_findings_map(new_findings)
    
    # Track processed keys to avoid double-counting
    processed_keys: set[str] = set()
    
    # Process all keys from old findings (check for Fixed, Regression, Still Failing)
    for key, old_f in old_map.items():
        processed_keys.add(key)
        
        old_status = FindingStatus.from_string(old_f.get("status"))
        old_excepted = key in old_exceptions
        
        # Check instance validity
        instance_scanned = is_instance_valid(key, valid_instance_keys)
        
        # Get new status
        if key in new_map:
            new_f = new_map[key]
            new_status = FindingStatus.from_string(new_f.get("status"))
            new_reason = new_f.get("reason", "")
        else:
            new_status = None
            new_reason = old_f.get("reason", "")
        
        new_excepted = key in new_exceptions
        
        # Classify transition
        transition = classify_finding_transition(
            old_status=old_status,
            new_status=new_status,
            old_has_exception=old_excepted,
            new_has_exception=new_excepted,
            instance_was_scanned=instance_scanned,
        )
        
        # Create change record if loggable
        if transition.should_log:
            server, instance = extract_server_instance(key)
            entity_type = derive_entity_type(key)
            
            change = DetectedChange(
                entity_type=entity_type,
                entity_key=key,
                change_type=transition.change_type,
                description=f"{transition.change_type.value}: {new_reason or key}",
                risk_level=RiskLevel.HIGH if transition.change_type == ChangeType.REGRESSION else RiskLevel.LOW,
                old_value=old_f.get("status"),
                new_value=new_map.get(key, {}).get("status"),
                server=server,
                instance=instance,
            )
            
            # Add to appropriate list and increment count
            if transition.change_type == ChangeType.FIXED:
                result.fixed.append(change)
                result.fixed_count += 1
            elif transition.change_type == ChangeType.REGRESSION:
                result.regressions.append(change)
                result.regression_count += 1
            elif transition.change_type == ChangeType.EXCEPTION_ADDED:
                result.exception_changes.append(change)
                result.exception_added_count += 1
            elif transition.change_type == ChangeType.EXCEPTION_REMOVED:
                result.exception_changes.append(change)
                result.exception_removed_count += 1
        
        # Count still failing (not logged, but tracked for stats)
        if transition.change_type == ChangeType.STILL_FAILING:
            if not new_excepted:  # Only count if not exceptioned
                result.still_failing_count += 1
    
    # Process new findings not in old (check for New Issues)
    for key, new_f in new_map.items():
        if key in processed_keys:
            continue  # Already processed
        
        new_status = FindingStatus.from_string(new_f.get("status"))
        new_excepted = key in new_exceptions
        
        # Classify as new item
        transition = classify_finding_transition(
            old_status=None,  # Didn't exist before
            new_status=new_status,
            old_has_exception=False,
            new_has_exception=new_excepted,
            instance_was_scanned=True,  # If it's in new, instance was reached
        )
        
        if transition.should_log and transition.change_type == ChangeType.NEW_ISSUE:
            server, instance = extract_server_instance(key)
            entity_type = derive_entity_type(key)
            
            change = DetectedChange(
                entity_type=entity_type,
                entity_key=key,
                change_type=ChangeType.NEW_ISSUE,
                description=f"New Issue: {new_f.get('reason', key)}",
                risk_level=RiskLevel.HIGH,
                new_value=new_f.get("status"),
                server=server,
                instance=instance,
            )
            
            result.new_issues.append(change)
            result.new_issue_count += 1
    
    return result


def get_exception_keys(
    findings: list[dict[str, Any]],
    annotations: dict[str, dict[str, Any]],
) -> set[str]:
    """
    Get set of entity keys that are validly exceptioned.
    
    A finding is exceptioned if:
    1. It's discrepant (FAIL/WARN)
    2. It has justification OR review_status == "Exception"
    
    Args:
        findings: List of findings
        annotations: Dict of entity_key -> annotation
        
    Returns:
        Set of entity keys with valid exceptions
    """
    from autodbaudit.domain.state_machine import is_exception_eligible
    
    result = set()
    for f in findings:
        key = f.get("entity_key", "")
        status = FindingStatus.from_string(f.get("status"))
        
        if status and status.is_discrepant() and key in annotations:
            ann = annotations[key]
            if is_exception_eligible(
                status=status,
                has_justification=bool(ann.get("justification")),
                review_status=ann.get("review_status"),
            ):
                result.add(key)
    
    return result
