"""
Action Detector - Detects all actions from various change sources.

This module consolidates detected changes from:
- Findings diff (Fixed, Regression, New Issue)
- Exception changes
- Entity mutations

Architecture Note:
    - Pure functions, no database I/O
    - Combines changes from multiple sources
    - Applies priority rules for concurrent changes
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autodbaudit.domain.change_types import (
    ChangeType,
    DetectedChange,
    EntityType,
    RiskLevel,
)
from autodbaudit.domain.state_machine import resolve_concurrent_changes
from autodbaudit.application.diff.findings_diff import FindingsDiffResult


def detect_all_actions(
    findings_diff: FindingsDiffResult,
    exception_changes: list[DetectedChange] | None = None,
    entity_changes: list[DetectedChange] | None = None,
    detected_at: datetime | None = None,
) -> list[DetectedChange]:
    """
    Consolidate all detected actions from various sources.
    
    This is the main entry point for action detection.
    It combines findings changes, exception changes, and entity mutations
    into a single list of actions to record.
    
    Args:
        findings_diff: Result from diff_findings()
        exception_changes: Changes detected by annotation sync
        entity_changes: Changes detected by entity diff
        detected_at: Timestamp for all actions (default: now)
        
    Returns:
        List of DetectedChange objects ready for recording
    """
    detected_at = detected_at or datetime.now(timezone.utc)
    exception_changes = exception_changes or []
    entity_changes = entity_changes or []
    
    all_actions: list[DetectedChange] = []
    
    # Add findings changes
    all_actions.extend(findings_diff.fixed)
    all_actions.extend(findings_diff.regressions)
    all_actions.extend(findings_diff.new_issues)
    all_actions.extend(findings_diff.exception_changes)
    
    # Add external exception changes (from annotation sync)
    all_actions.extend(exception_changes)
    
    # Add entity changes
    all_actions.extend(entity_changes)
    
    # Update timestamps if not set
    for action in all_actions:
        if action.detected_at is None:
            # Create new dataclass with updated timestamp
            object.__setattr__(action, 'detected_at', detected_at)
    
    return all_actions


def consolidate_actions(
    actions: list[DetectedChange],
) -> list[DetectedChange]:
    """
    Consolidate actions for the same entity (priority resolution).
    
    When multiple changes are detected for the same entity_key,
    apply priority rules to determine the final action.
    
    Priority order:
    1. FIXED (highest)
    2. REGRESSION
    3. NEW_ISSUE
    4. EXCEPTION_ADDED
    5. EXCEPTION_REMOVED
    6. ENTITY_* changes
    7. STILL_FAILING (lowest, usually not logged)
    
    Args:
        actions: List of detected actions
        
    Returns:
        Consolidated list with one action per entity_key
    """
    # Group by entity_key
    by_key: dict[str, list[DetectedChange]] = {}
    for action in actions:
        key = action.entity_key
        if key not in by_key:
            by_key[key] = []
        by_key[key].append(action)
    
    # Resolve conflicts
    result: list[DetectedChange] = []
    for key, key_actions in by_key.items():
        if len(key_actions) == 1:
            result.append(key_actions[0])
        else:
            # Sort by priority (lower = higher priority)
            sorted_actions = sorted(
                key_actions,
                key=lambda a: a.change_type.priority
            )
            # Take highest priority action
            winner = sorted_actions[0]
            result.append(winner)
    
    return result


def create_exception_action(
    entity_key: str,
    justification: str,
    change_type: ChangeType = ChangeType.EXCEPTION_ADDED,
    server: str = "",
    instance: str = "",
) -> DetectedChange:
    """
    Create an exception change action.
    
    Args:
        entity_key: The entity key
        justification: The justification text
        change_type: EXCEPTION_ADDED, EXCEPTION_REMOVED, or EXCEPTION_UPDATED
        server: Server name
        instance: Instance name
        
    Returns:
        DetectedChange for the exception
    """
    # Derive entity type from key
    parts = entity_key.split("|")
    entity_type = EntityType.CONFIGURATION
    if parts:
        type_map = {
            "sa_account": EntityType.SA_ACCOUNT,
            "login": EntityType.LOGIN,
            "config": EntityType.CONFIGURATION,
            "service": EntityType.SERVICE,
            "database": EntityType.DATABASE,
            "backup": EntityType.BACKUP,
        }
        entity_type = type_map.get(parts[0].lower(), EntityType.CONFIGURATION)
    
    # Truncate justification for description
    truncated = justification[:50] + "..." if len(justification) > 50 else justification
    
    if change_type == ChangeType.EXCEPTION_REMOVED:
        description = f"Exception Removed (was: {truncated})"
    elif change_type == ChangeType.EXCEPTION_UPDATED:
        description = f"Exception Updated: {truncated}"
    else:
        description = f"Exception Documented: {truncated}"
    
    return DetectedChange(
        entity_type=entity_type,
        entity_key=entity_key,
        change_type=change_type,
        description=description,
        risk_level=RiskLevel.INFO,
        new_value=justification,
        server=server,
        instance=instance,
        detected_at=datetime.now(timezone.utc),
    )


def create_fix_action(
    entity_key: str,
    reason: str = "",
    server: str = "",
    instance: str = "",
) -> DetectedChange:
    """
    Create a fix action.
    
    Args:
        entity_key: The entity key
        reason: Description of what was fixed
        server: Server name
        instance: Instance name
        
    Returns:
        DetectedChange for the fix
    """
    parts = entity_key.split("|")
    entity_type = EntityType.CONFIGURATION
    if parts:
        type_map = {
            "sa_account": EntityType.SA_ACCOUNT,
            "login": EntityType.LOGIN,
            "config": EntityType.CONFIGURATION,
            "service": EntityType.SERVICE,
        }
        entity_type = type_map.get(parts[0].lower(), EntityType.CONFIGURATION)
    
    return DetectedChange(
        entity_type=entity_type,
        entity_key=entity_key,
        change_type=ChangeType.FIXED,
        description=f"Fixed: {reason or 'Issue resolved'}",
        risk_level=RiskLevel.LOW,
        server=server,
        instance=instance,
        detected_at=datetime.now(timezone.utc),
    )


def create_regression_action(
    entity_key: str,
    reason: str = "",
    server: str = "",
    instance: str = "",
) -> DetectedChange:
    """
    Create a regression action.
    
    Args:
        entity_key: The entity key
        reason: Description of the regression
        server: Server name
        instance: Instance name
        
    Returns:
        DetectedChange for the regression
    """
    parts = entity_key.split("|")
    entity_type = EntityType.CONFIGURATION
    if parts:
        type_map = {
            "sa_account": EntityType.SA_ACCOUNT,
            "login": EntityType.LOGIN,
            "config": EntityType.CONFIGURATION,
        }
        entity_type = type_map.get(parts[0].lower(), EntityType.CONFIGURATION)
    
    return DetectedChange(
        entity_type=entity_type,
        entity_key=entity_key,
        change_type=ChangeType.REGRESSION,
        description=f"Regression: {reason or 'Issue re-appeared'}",
        risk_level=RiskLevel.HIGH,
        server=server,
        instance=instance,
        detected_at=datetime.now(timezone.utc),
    )
