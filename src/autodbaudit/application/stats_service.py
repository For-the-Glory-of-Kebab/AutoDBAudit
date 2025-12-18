"""
Stats Service - Single Source of Truth for All Statistics.

This module provides THE authoritative source for all sync statistics.
All consumers (CLI, Excel Cover Sheet, --finalize) MUST use this service.

Architecture Note:
    - Depends only on domain types and HistoryStore
    - No direct Excel or CLI coupling
    - Computes stats fresh each time (no caching)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, Any

from autodbaudit.domain.change_types import (
    FindingStatus,
    SyncStats,
)
from autodbaudit.domain.state_machine import (
    classify_finding_transition,
    is_exception_eligible,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols (Interfaces)
# =============================================================================

class FindingsProvider(Protocol):
    """Protocol for providing findings data."""
    
    def get_findings(self, run_id: int) -> list[dict[str, Any]]:
        """Get findings for a specific run."""
        ...


class AnnotationsProvider(Protocol):
    """Protocol for providing annotation data."""
    
    def get_all_annotations(self) -> dict[str, dict[str, Any]]:
        """Get all annotations keyed by entity_key."""
        ...


class InstanceValidator(Protocol):
    """Protocol for validating instance availability."""
    
    def get_scanned_instance_keys(self, run_id: int) -> set[str]:
        """Get set of 'Server|Instance' keys that were scanned."""
        ...


# =============================================================================
# Helper Classes
# =============================================================================

@dataclass
class DiffResult:
    """Result of diffing two findings lists."""
    fixed: int = 0
    regressions: int = 0
    new_issues: int = 0
    still_failing: int = 0
    exceptions_added: int = 0


# =============================================================================
# Stats Service
# =============================================================================

class StatsService:
    """
    Single source of truth for all sync statistics.
    
    All consumers (CLI, Excel Cover, --finalize) use this service.
    This ensures consistent stats everywhere.
    
    Usage:
        service = StatsService(store, annotation_provider)
        stats = service.calculate(baseline_id, current_id)
        
        # For CLI
        print(f"Fixed: {stats.fixed_since_baseline}")
        
        # For Excel Cover
        cover_data = stats.to_dict()
    """
    
    def __init__(
        self,
        findings_provider: FindingsProvider,
        annotations_provider: AnnotationsProvider,
        instance_validator: InstanceValidator | None = None,
    ):
        """
        Initialize stats service.
        
        Args:
            findings_provider: Source for findings data (usually HistoryStore)
            annotations_provider: Source for annotations (usually AnnotationSyncService)
            instance_validator: Optional validator for scanned instances
        """
        self.findings = findings_provider
        self.annotations = annotations_provider
        self.instance_validator = instance_validator
    
    def calculate(
        self,
        baseline_run_id: int,
        current_run_id: int,
        previous_run_id: int | None = None,
    ) -> SyncStats:
        """
        Calculate all statistics.
        
        Args:
            baseline_run_id: Initial audit run ID
            current_run_id: Current sync run ID
            previous_run_id: Previous sync run ID (if exists)
            
        Returns:
            SyncStats with all computed values
        """
        # Fetch data
        baseline_findings = self.findings.get_findings(baseline_run_id)
        current_findings = self.findings.get_findings(current_run_id)
        annotations = self.annotations.get_all_annotations()
        
        # Get valid instances for current run
        valid_instances: set[str] = set()
        if self.instance_validator:
            valid_instances = self.instance_validator.get_scanned_instance_keys(
                current_run_id
            )
        
        # Calculate current state
        active_issues = self._count_active_issues(current_findings, annotations)
        exceptions = self._count_exceptions(current_findings, annotations)
        compliant = self._count_compliant(current_findings)
        
        # Calculate changes from baseline
        baseline_diff = self._diff_findings(
            old_findings=baseline_findings,
            new_findings=current_findings,
            annotations=annotations,
            valid_instances=valid_instances,
        )
        
        # Calculate changes from previous sync
        if previous_run_id and previous_run_id != baseline_run_id:
            prev_findings = self.findings.get_findings(previous_run_id)
            recent_diff = self._diff_findings(
                old_findings=prev_findings,
                new_findings=current_findings,
                annotations=annotations,
                valid_instances=valid_instances,
            )
        else:
            recent_diff = baseline_diff
        
        return SyncStats(
            total_findings=len(current_findings),
            active_issues=active_issues,
            documented_exceptions=exceptions,
            compliant_items=compliant,
            fixed_since_baseline=baseline_diff.fixed,
            regressions_since_baseline=baseline_diff.regressions,
            new_issues_since_baseline=baseline_diff.new_issues,
            exceptions_added_since_baseline=baseline_diff.exceptions_added,
            fixed_since_last=recent_diff.fixed,
            regressions_since_last=recent_diff.regressions,
            new_issues_since_last=recent_diff.new_issues,
            exceptions_added_since_last=recent_diff.exceptions_added,
        )
    
    def _count_active_issues(
        self,
        findings: list[dict],
        annotations: dict[str, dict],
    ) -> int:
        """
        Count active issues (discrepant without exception).
        
        Active = FAIL/WARN AND NOT exceptioned
        """
        count = 0
        for finding in findings:
            status = FindingStatus.from_string(finding.get("status"))
            if status and status.is_discrepant():
                entity_key = finding.get("entity_key", "")
                if not self._is_exceptioned(entity_key, annotations):
                    count += 1
        return count
    
    def _count_exceptions(
        self,
        findings: list[dict],
        annotations: dict[str, dict],
    ) -> int:
        """
        Count documented exceptions (discrepant WITH exception).
        
        Exception = FAIL/WARN AND exceptioned
        """
        count = 0
        for finding in findings:
            status = FindingStatus.from_string(finding.get("status"))
            if status and status.is_discrepant():
                entity_key = finding.get("entity_key", "")
                if self._is_exceptioned(entity_key, annotations):
                    count += 1
        return count
    
    def _count_compliant(self, findings: list[dict]) -> int:
        """Count compliant items (PASS status)."""
        count = 0
        for finding in findings:
            status = FindingStatus.from_string(finding.get("status"))
            if status == FindingStatus.PASS:
                count += 1
        return count
    
    def _is_exceptioned(
        self,
        entity_key: str,
        annotations: dict[str, dict],
    ) -> bool:
        """Check if entity has a valid exception."""
        if entity_key not in annotations:
            return False
        
        ann = annotations[entity_key]
        return is_exception_eligible(
            status=FindingStatus.FAIL,  # If we're checking, assume discrepant
            has_justification=bool(ann.get("justification")),
            review_status=ann.get("review_status"),
        )
    
    def _diff_findings(
        self,
        old_findings: list[dict],
        new_findings: list[dict],
        annotations: dict[str, dict],
        valid_instances: set[str],
    ) -> DiffResult:
        """
        Diff two findings lists using the state machine.
        
        Args:
            old_findings: Previous findings
            new_findings: Current findings
            annotations: Current annotation state
            valid_instances: Set of scanned instance keys
            
        Returns:
            DiffResult with counts
        """
        result = DiffResult()
        
        # Build maps for efficient lookup
        old_map = {f["entity_key"]: f for f in old_findings}
        new_map = {f["entity_key"]: f for f in new_findings}
        
        # Check for instance validity
        check_validity = len(valid_instances) > 0
        
        # Process old → new transitions
        for key, old_f in old_map.items():
            old_status = FindingStatus.from_string(old_f.get("status"))
            
            # Check instance validity
            instance_scanned = True
            if check_validity:
                instance_scanned = self._is_valid_instance_key(key, valid_instances)
            
            if key in new_map:
                new_f = new_map[key]
                new_status = FindingStatus.from_string(new_f.get("status"))
            else:
                new_status = None  # Item disappeared
            
            # Get exception states
            old_excepted = self._is_exceptioned(key, {})  # No old annotations
            new_excepted = self._is_exceptioned(key, annotations)
            
            # Classify transition
            transition = classify_finding_transition(
                old_status=old_status,
                new_status=new_status,
                old_has_exception=old_excepted,
                new_has_exception=new_excepted,
                instance_was_scanned=instance_scanned,
            )
            
            # Count by type
            from autodbaudit.domain.change_types import ChangeType
            if transition.change_type == ChangeType.FIXED:
                result.fixed += 1
            elif transition.change_type == ChangeType.REGRESSION:
                result.regressions += 1
            elif transition.change_type == ChangeType.EXCEPTION_ADDED:
                result.exceptions_added += 1
            elif transition.change_type == ChangeType.STILL_FAILING:
                if not new_excepted:  # Only count if not exceptioned
                    result.still_failing += 1
        
        # Check for new issues (in new but not in old)
        for key, new_f in new_map.items():
            if key not in old_map:
                new_status = FindingStatus.from_string(new_f.get("status"))
                if new_status and new_status.is_discrepant():
                    # Only count if not already exceptioned
                    if not self._is_exceptioned(key, annotations):
                        result.new_issues += 1
        
        return result
    
    def _is_valid_instance_key(
        self,
        entity_key: str,
        valid_instances: set[str],
    ) -> bool:
        """
        Check if entity key belongs to a scanned instance.
        
        Keys typically have format: Type|Server|Instance|... or Server|Instance|...
        """
        if not valid_instances:
            return True  # If no validation, assume valid
        
        key_lower = entity_key.lower()
        parts = key_lower.split("|")
        
        for valid in valid_instances:
            valid_lower = valid.lower()
            
            # Try Type|Server|Instance format
            if len(parts) >= 3:
                if f"{parts[1]}|{parts[2]}" == valid_lower:
                    return True
            
            # Try Server|Instance format
            if len(parts) >= 2:
                if f"{parts[0]}|{parts[1]}" == valid_lower:
                    return True
        
        return False


# =============================================================================
# CLI Output Formatting
# =============================================================================

def format_cli_stats(stats: SyncStats, use_color: bool = True) -> str:
    """
    Format stats for CLI output.
    
    Args:
        stats: Computed SyncStats
        use_color: Whether to use ANSI colors
        
    Returns:
        Formatted string for CLI display
    """
    # Colors
    if use_color:
        GREEN = "\033[92m"
        RED = "\033[91m"
        YELLOW = "\033[93m"
        CYAN = "\033[96m"
        RESET = "\033[0m"
        CHECK = "✅"
        CROSS = "❌"
        WARN = "⚠️"
        DOC = "📋"
        CHART = "📊"
    else:
        GREEN = RED = YELLOW = CYAN = RESET = ""
        CHECK = "[OK]"
        CROSS = "[X]"
        WARN = "[!]"
        DOC = "[D]"
        CHART = "[S]"
    
    lines = [
        f"\n{CHART} {CYAN}Sync Summary{RESET}",
        f"{'━' * 45}",
        "",
        f"📈 {CYAN}Changes Since Baseline:{RESET}",
        f"   {CHECK} Fixed:        {GREEN}{stats.fixed_since_baseline}{RESET}",
        f"   {CROSS} Regressed:    {RED}{stats.regressions_since_baseline}{RESET}",
        f"   {WARN} New Issues:   {YELLOW}{stats.new_issues_since_baseline}{RESET}",
        "",
        f"{DOC} {CYAN}Current State:{RESET}",
        f"   {CROSS} Active Issues:     {RED}{stats.active_issues}{RESET}",
        f"   {CHECK} Exceptions:        {GREEN}{stats.documented_exceptions}{RESET}",
        f"   {CHECK} Compliant Items:   {GREEN}{stats.compliant_items}{RESET}",
        "",
        f"{'━' * 45}",
    ]
    
    return "\n".join(lines)


def format_cli_stats_compact(stats: SyncStats) -> str:
    """Compact one-line stats for CLI."""
    return (
        f"Fixed: {stats.fixed_since_baseline} | "
        f"Active: {stats.active_issues} | "
        f"Exceptions: {stats.documented_exceptions} | "
        f"Regressions: {stats.regressions_since_baseline}"
    )
