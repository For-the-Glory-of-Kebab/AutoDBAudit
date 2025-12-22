"""
Stats Service - Single Source of Truth for All Statistics.

This module provides THE authoritative source for all sync statistics.
All consumers (CLI, Excel Cover Sheet, --finalize) MUST use this service.

Architecture Note:
    - Depends only on domain types and HistoryStore
    - No direct Excel or CLI coupling
    - Computes stats fresh each time (no caching)
    - All key comparisons are case-insensitive (normalized to lowercase)
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
from autodbaudit.domain.entity_key import normalize_key_string

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

from collections import defaultdict, Counter
from dataclasses import field


@dataclass
class DiffResult:
    """Result of diffing two findings lists."""

    fixed: int = 0
    regressions: int = 0
    new_issues: int = 0
    still_failing: int = 0
    exceptions_added: int = 0
    exceptions_removed: int = 0
    exceptions_updated: int = 0
    docs_added: int = 0
    docs_updated: int = 0
    docs_removed: int = 0
    # sheet_name -> stat_name -> count
    sheet_stats: dict[str, dict[str, int]] = field(default_factory=dict)


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
        # NOTE: For baseline comparison, we ideally need baseline annotations.
        # However, annotations are typically "current state" of the UI.
        # If we want true history of docs, we'd need to fetch historical annotations.
        # For now, we assume annotations are compared "Last Sync vs Current".
        # Baseline comparison uses current annotations for both sides to filter exceptions,
        # but doesn't track "Docs Changed Since Baseline" (that's too noisy/hard).
        baseline_diff = self._diff_findings(
            old_findings=baseline_findings,
            new_findings=current_findings,
            old_annotations=annotations,  # Use current as proxy? Or empty?
            # Actually, "Docs Changed" only makes sense for "Recent Sync".
            # For Baseline, we just want exception counts.
            new_annotations=annotations,
            valid_instances=valid_instances,
        )

        # Calculate changes from previous sync
        if previous_run_id and previous_run_id != baseline_run_id:
            prev_findings = self.findings.get_findings(previous_run_id)

            # TODO: We need PREVIOUS annotations to diff docs!
            # If we don't have them, we can't count docs_added/updated correctly.
            # HistoryStore doesn't currently version annotations (they are just persistent).
            # This is a limitation: Annotations are overwrites.
            # To fix this properly, we'd need to load "Annotation State at Run X".
            # Since we can't do that yet without schema change, we might need to skip doc diffs
            # OR rely on Action Log 'update_annotation' events if we had them.

            # WORKAROUND: Use Actions recorded this sync for exception counts
            # instead of broken annotation diff (which uses same annotations for both)
            recent_diff = self._diff_findings(
                old_findings=prev_findings,
                new_findings=current_findings,
                old_annotations=annotations,
                new_annotations=annotations,
                valid_instances=valid_instances,
            )
        else:
            recent_diff = baseline_diff

        # Get exception counts from RECORDED ACTIONS (the correct source)
        # This fixes the "No recent documentation changes detected" issue
        action_counts = self._count_recent_actions(baseline_run_id, current_run_id)

        return SyncStats(
            total_findings=len(current_findings),
            active_issues=active_issues,
            documented_exceptions=exceptions,
            compliant_items=compliant,
            fixed_since_baseline=baseline_diff.fixed,
            regressions_since_baseline=baseline_diff.regressions,
            new_issues_since_baseline=baseline_diff.new_issues,
            # Use action log for baseline exceptions (diff is broken when using same annotations)
            exceptions_added_since_baseline=action_counts.get("exceptions_added", 0),
            fixed_since_last=recent_diff.fixed,
            regressions_since_last=recent_diff.regressions,
            new_issues_since_last=recent_diff.new_issues,
            # Use action log counts instead of broken diff counts
            exceptions_added_since_last=action_counts.get("exceptions_added", 0),
            exceptions_removed_since_last=action_counts.get("exceptions_removed", 0),
            exceptions_updated_since_last=action_counts.get("exceptions_updated", 0),
            docs_added_since_last=action_counts.get("docs_added", 0),
            docs_updated_since_last=action_counts.get("docs_updated", 0),
            docs_removed_since_last=action_counts.get("docs_removed", 0),
            # Build current state per-sheet stats (not just changes)
            sheet_stats=self._build_current_sheet_stats(current_findings, annotations),
        )

    def _count_recent_actions(
        self,
        initial_run_id: int,
        current_run_id: int,
    ) -> dict[str, int]:
        """
        Count recent actions from the action log.

        This uses the actual recorded actions instead of trying to diff
        annotations (which are not versioned and thus always appear identical).

        Args:
            initial_run_id: Baseline run ID
            current_run_id: Current sync run ID

        Returns:
            Dict with counts: exceptions_added, exceptions_removed, etc.
        """
        counts = {
            "exceptions_added": 0,
            "exceptions_removed": 0,
            "exceptions_updated": 0,
            "docs_added": 0,
            "docs_updated": 0,
            "docs_removed": 0,
        }

        # Get actions for this baseline, filter by current sync run
        if not hasattr(self.findings, "get_actions_for_run"):
            return counts

        try:
            all_actions = self.findings.get_actions_for_run(initial_run_id)
        except Exception:
            return counts

        # Filter to actions recorded in this sync run
        for action in all_actions:
            if action.get("sync_run_id") != current_run_id:
                continue

            action_type = action.get("action_type", "").lower()

            # Map action types to counts
            # Actual values: "Exception Documented", "Exception Removed", "Exception Updated"
            # Also handle legacy: "exception_added", etc.
            if "exception" in action_type:
                if "documented" in action_type or "added" in action_type:
                    counts["exceptions_added"] += 1
                elif "removed" in action_type:
                    counts["exceptions_removed"] += 1
                elif "updated" in action_type:
                    counts["exceptions_updated"] += 1
            elif "doc" in action_type or "note" in action_type:
                if "added" in action_type:
                    counts["docs_added"] += 1
                elif "removed" in action_type:
                    counts["docs_removed"] += 1
                elif "updated" in action_type:
                    counts["docs_updated"] += 1

        return counts

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

    def _build_current_sheet_stats(
        self,
        findings: list[dict],
        annotations: dict[str, dict],
    ) -> dict[str, dict[str, int]]:
        """
        Build per-sheet breakdown of current state.
        
        Returns dict of {sheet_name: {active: X, exceptions: X, compliant: X}}
        """
        sheet_stats: dict[str, dict[str, int]] = {}
        
        for finding in findings:
            finding_type = finding.get("finding_type", "")
            sheet_name = self._get_sheet_name_from_finding_type(finding_type)
            
            if not sheet_name:
                continue
            
            if sheet_name not in sheet_stats:
                sheet_stats[sheet_name] = defaultdict(int)
            
            status = FindingStatus.from_string(finding.get("status"))
            entity_key = finding.get("entity_key", "")
            
            if status == FindingStatus.PASS:
                sheet_stats[sheet_name]["compliant"] += 1
            elif status and status.is_discrepant():
                if self._is_exceptioned(entity_key, annotations):
                    sheet_stats[sheet_name]["exceptions"] += 1
                else:
                    sheet_stats[sheet_name]["active"] += 1
        
        return sheet_stats

    def _is_exceptioned(
        self,
        entity_key: str,
        annotations: dict[str, dict],
    ) -> bool:
        """Check if entity has a valid exception.

        Note: Annotations are keyed as 'entity_type|entity_key' but findings
        only have 'entity_key'. We must try all known type prefixes.
        All comparisons are case-insensitive (normalized to lowercase).
        """
        # Normalize the entity_key to lowercase for matching
        normalized_entity_key = normalize_key_string(entity_key)

        # Build a lowercase lookup map for annotations
        # This is done each time for simplicity; could be cached if performance matters
        normalized_annotations = {
            normalize_key_string(k): v for k, v in annotations.items()
        }

        # Try direct lookup first (in case key already includes type prefix)
        if normalized_entity_key in normalized_annotations:
            ann = normalized_annotations[normalized_entity_key]
            return is_exception_eligible(
                status=FindingStatus.FAIL,
                has_justification=bool(ann.get("justification")),
                review_status=ann.get("review_status"),
            )

        # Try all known entity type prefixes
        KNOWN_TYPES = [
            "sa_account",
            "login",
            "server_role_member",
            "config",
            "service",
            "database",
            "db_user",
            "db_role",
            "permission",
            "orphaned_user",
            "trigger",
            "protocol",
            "backup",
            "audit_settings",
            "encryption",
            "linked_server",
            "instance",
        ]

        for etype in KNOWN_TYPES:
            prefixed_key = f"{etype}|{normalized_entity_key}"
            if prefixed_key in normalized_annotations:
                ann = normalized_annotations[prefixed_key]
                return is_exception_eligible(
                    status=FindingStatus.FAIL,
                    has_justification=bool(ann.get("justification")),
                    review_status=ann.get("review_status"),
                )

        return False

    def _diff_findings(
        self,
        old_findings: list[dict],
        new_findings: list[dict],
        old_annotations: dict[str, dict],
        new_annotations: dict[str, dict],
        valid_instances: set[str],
    ) -> DiffResult:
        """
        Diff two findings lists using the state machine.

        Args:
            old_findings: Previous findings
            new_findings: Current findings
            old_annotations: Annotations at previous state (limit: often same as new)
            new_annotations: Current annotations
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
            # Use same annotations for old check because annotations are persistent/timeless
            old_excepted = self._is_exceptioned(key, old_annotations)
            new_excepted = self._is_exceptioned(key, new_annotations)

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

            # Resolve sheet name from finding_type (not entity_key which lacks type prefix)
            finding_type = old_f.get("finding_type", "")
            sheet_name = self._get_sheet_name_from_finding_type(finding_type)
            if sheet_name:
                if sheet_name not in result.sheet_stats:
                    result.sheet_stats[sheet_name] = defaultdict(int)
                stats = result.sheet_stats[sheet_name]

            if transition.change_type == ChangeType.FIXED:
                result.fixed += 1
                if sheet_name:
                    stats["fixed"] += 1
            elif transition.change_type == ChangeType.REGRESSION:
                result.regressions += 1
                if sheet_name:
                    stats["regressions"] += 1
            elif transition.change_type == ChangeType.EXCEPTION_ADDED:
                result.exceptions_added += 1
                if sheet_name:
                    stats["exceptions_added"] += 1
            elif transition.change_type == ChangeType.EXCEPTION_REMOVED:
                result.exceptions_removed += 1
                if sheet_name:
                    stats["exceptions_removed"] += 1
            elif transition.change_type == ChangeType.EXCEPTION_UPDATED:
                result.exceptions_updated += 1
                if sheet_name:
                    stats["exceptions_updated"] += 1
            elif transition.change_type == ChangeType.STILL_FAILING:
                if not new_excepted:  # Only count if not exceptioned
                    result.still_failing += 1
                    if sheet_name:
                        stats["active"] += 1

        # Check for documentation changes (Notes/Dates) on ALL items
        # This runs independently of status changes
        if old_annotations and new_annotations:
            for key, new_ann in new_annotations.items():
                if check_validity and not self._is_valid_instance_key(
                    key, valid_instances
                ):
                    continue

        # Check for documentation changes (Notes/Dates) on ALL items
        # This runs independently of status changes
        if old_annotations and new_annotations:
            # Check for Additions / Updates
            for key, new_ann in new_annotations.items():
                if check_validity and not self._is_valid_instance_key(
                    key, valid_instances
                ):
                    continue

                new_has = self._has_docs(new_ann)

                if key not in old_annotations:
                    # New annotation key
                    if new_has:
                        result.docs_added += 1
                else:
                    # Existing annotation key
                    old_ann = old_annotations[key]
                    old_has = self._has_docs(old_ann)

                    if not old_has and new_has:
                        # Existing key, but docs newly added
                        result.docs_added += 1
                    elif old_has and not new_has:
                        # Existing key, docs cleared (counted as removed here or below?)
                        # We handle removed keys below perfectly.
                        # But if key stays and docs are cleared, we count removed here.
                        result.docs_removed += 1
                    elif old_has and new_has:
                        # Both have docs, check if changed
                        if self._has_docs_changed(old_ann, new_ann):
                            result.docs_updated += 1

            # Check for Removed Keys (where key itself disappears)
            for key, old_ann in old_annotations.items():
                if check_validity and not self._is_valid_instance_key(
                    key, valid_instances
                ):
                    continue

                if key not in new_annotations:
                    if self._has_docs(old_ann):
                        result.docs_removed += 1

        # Check for new issues (in new but not in old)
        for key, new_f in new_map.items():
            if key not in old_map:
                new_status = FindingStatus.from_string(new_f.get("status"))
                if new_status and new_status.is_discrepant():
                    # Only count if not already exceptioned
                    if not self._is_exceptioned(key, new_annotations):
                        result.new_issues += 1
                        # Track sheet stat for NEW ISSUE (use finding_type, not key)
                        finding_type = new_f.get("finding_type", "")
                        sheet_name = self._get_sheet_name_from_finding_type(finding_type)
                        if sheet_name:
                            if sheet_name not in result.sheet_stats:
                                result.sheet_stats[sheet_name] = defaultdict(int)
                            result.sheet_stats[sheet_name]["new_issues"] += 1

        return result

    def _get_sheet_name_from_key(self, key: str) -> str:
        """Derive readable sheet name from entity key prefix."""
        # This mapping should match SHEET_ANNOTATION_CONFIG keys in annotation_sync
        # or be readable enough for the user.
        parts = key.split("|")
        if not parts:
            return "Unknown"

        etype = parts[0].lower()
        mapping = {
            "instance": "Instances",
            "sa_account": "SA Account",
            "login": "Server Logins",
            "server_role_member": "Sensitive Roles",
            "config": "Configuration",
            "service": "Services",
            "database": "Databases",
            "db_user": "Database Users",
            "db_role": "Database Roles",
            "permission": "Permission Grants",
            "orphaned_user": "Orphaned Users",
            "linked_server": "Linked Servers",
            "trigger": "Triggers",
            "protocol": "Client Protocols",
            "backup": "Backups",
            "audit_settings": "Audit Settings",
            "encryption": "Encryption",
        }
        return mapping.get(etype, etype.capitalize())

    def _get_sheet_name_from_finding_type(self, finding_type: str) -> str:
        """Derive readable sheet name from finding_type field directly."""
        if not finding_type:
            return ""
        
        etype = finding_type.lower().strip()
        mapping = {
            "instance": "Instances",
            "sa_account": "SA Account",
            "login": "Server Logins",
            "server_role_member": "Sensitive Roles",
            "config": "Configuration",
            "service": "Services",
            "database": "Databases",
            "db_user": "Database Users",
            "db_role": "Database Roles",
            "permission": "Permission Grants",
            "orphaned_user": "Orphaned Users",
            "linked_server": "Linked Servers",
            "trigger": "Triggers",
            "protocol": "Client Protocols",
            "backup": "Backups",
            "audit_settings": "Audit Settings",
            "encryption": "Encryption",
        }
        return mapping.get(etype, etype.replace("_", " ").title())

    def _has_docs(self, fields: dict) -> bool:
        """Check if annotation has non-exception documentation (Notes/Date)."""
        # Justification is for Exceptions. Notes/Dates are for docs.
        # We only count Notes and Dates here.
        if fields.get("notes") and str(fields["notes"]).strip():
            return True

        # Check date fields
        for k, v in fields.items():
            if "date" in k.lower() or "reviewed" in k.lower() or "revised" in k.lower():
                if v and str(v).strip():
                    return True
        return False

    def _has_docs_changed(self, old: dict, new: dict) -> bool:
        """Check if documentation fields changed."""
        # Check Notes
        if str(old.get("notes", "")).strip() != str(new.get("notes", "")).strip():
            return True

        # Check Dates
        # Iterate all keys in both
        all_keys = set(old.keys()) | set(new.keys())
        for k in all_keys:
            if "date" in k.lower() or "reviewed" in k.lower() or "revised" in k.lower():
                if str(old.get(k, "")).strip() != str(new.get(k, "")).strip():
                    return True
        return False

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
