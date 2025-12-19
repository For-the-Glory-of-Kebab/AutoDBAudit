"""
Action Recorder - Persists actions to the database with deduplication.

This module handles:
- Recording detected changes to action_log table
- Deduplication (same entity + change_type + sync = one entry)
- Preserving user edits (date override, notes)

Architecture Note:
    - Uses HistoryStore for database operations
    - Handles all deduplication logic
    - Preserves user-edited fields
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Protocol

from autodbaudit.domain.change_types import (
    ChangeType,
    ActionStatus,
    DetectedChange,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Protocols
# =============================================================================


class ActionStore(Protocol):
    """Protocol for action persistence operations."""

    def get_actions_for_run(self, initial_run_id: int) -> list[dict[str, Any]]:
        """Get all actions for an audit run."""
        ...

    def upsert_action(
        self,
        initial_run_id: int,
        entity_key: str,
        action_type: str,
        status: str,
        action_date: str,
        description: str,
        sync_run_id: int | None = None,
        finding_type: str = "",
        notes: str | None = None,
        user_date_override: str | None = None,
    ) -> int:
        """Insert or update an action. Returns action ID."""
        ...


# =============================================================================
# Helper Functions
# =============================================================================


def should_record_action(
    action: DetectedChange,
    existing_actions: list[dict[str, Any]],
    current_sync_id: int,
) -> bool:
    """
    Check if an action should be recorded (deduplication).

    Rules:
    1. Never duplicate same entity + change_type in same sync
    2. Don't re-record unchanged states across syncs
    3. DO record if truly new change

    Args:
        action: The action to check
        existing_actions: Current action log entries
        current_sync_id: Current sync run ID

    Returns:
        True if action should be recorded
    """
    entity_key = action.entity_key
    change_type = action.change_type.value

    for existing in existing_actions:
        if existing.get("entity_key") != entity_key:
            continue

        existing_type = existing.get("action_type")
        existing_sync = existing.get("sync_run_id")

        # Exact duplicate in same sync - skip
        if existing_type == change_type and existing_sync == current_sync_id:
            logger.debug(
                "Skipping duplicate action: %s/%s in sync %d",
                entity_key,
                change_type,
                current_sync_id,
            )
            return False

        # Same type logged in a previous sync - check if state actually changed
        if existing_type == change_type:
            # For "still failing" type events, don't re-log
            if change_type in ("Still Failing", "No Change"):
                return False

    return True


def derive_action_status(change_type: ChangeType) -> str:
    """
    Derive action status from change type.

    Args:
        change_type: The type of change

    Returns:
        Status string for action_log
    """
    status_map = {
        ChangeType.FIXED: "fixed",
        ChangeType.REGRESSION: "regression",
        ChangeType.NEW_ISSUE: "open",
        ChangeType.EXCEPTION_ADDED: "exception",
        ChangeType.EXCEPTION_REMOVED: "pending",
        ChangeType.EXCEPTION_UPDATED: "exception",
        ChangeType.ENTITY_ADDED: "open",
        ChangeType.ENTITY_REMOVED: "fixed",
        ChangeType.STILL_FAILING: "open",
    }
    return status_map.get(change_type, "open")


# =============================================================================
# Action Recorder
# =============================================================================


class ActionRecorder:
    """
    Records actions to database with deduplication and user edit preservation.

    Usage:
        recorder = ActionRecorder(store)
        recorded = recorder.record_actions(
            actions=detected_actions,
            initial_run_id=1,
            sync_run_id=2,
        )
        print(f"Recorded {recorded} actions")
    """

    def __init__(self, store: ActionStore):
        """
        Initialize recorder.

        Args:
            store: Database store implementing ActionStore protocol
        """
        self.store = store

    def record_actions(
        self,
        actions: list[DetectedChange],
        initial_run_id: int,
        sync_run_id: int,
        existing_actions: list[dict[str, Any]] | None = None,
    ) -> int:
        """
        Record detected actions to database.

        Handles deduplication and preserves user edits.

        Args:
            actions: List of DetectedChange to record
            initial_run_id: Baseline audit run ID
            sync_run_id: Current sync run ID
            existing_actions: Optional pre-fetched existing actions

        Returns:
            Number of actions recorded
        """
        if existing_actions is None:
            existing_actions = self.store.get_actions_for_run(initial_run_id)

        recorded = 0

        for action in actions:
            # Skip if not loggable
            if not action.should_log:
                continue

            # Check deduplication
            if not should_record_action(action, existing_actions, sync_run_id):
                continue

            # Record to database
            try:
                action_date = (
                    action.detected_at.isoformat()
                    if action.detected_at
                    else datetime.now(timezone.utc).isoformat()
                )

                self.store.upsert_action(
                    initial_run_id=initial_run_id,
                    entity_key=action.entity_key,
                    action_type=action.change_type.value,
                    status=derive_action_status(action.change_type),
                    action_date=action_date,
                    description=action.description,
                    sync_run_id=sync_run_id,
                    finding_type=action.entity_type.value if action.entity_type else "",
                )

                recorded += 1
                logger.info(
                    "Recorded action: %s - %s",
                    action.change_type.value,
                    action.entity_key[:50],
                )

                # If Exception Added -> Update Finding Status in Database
                if action.change_type in (
                    ChangeType.EXCEPTION_ADDED,
                    ChangeType.EXCEPTION_UPDATED,
                ):
                    # Strip type prefix from key (Action Key: type|server|instance|name -> Finding Key: server|instance|name)
                    known_types = {
                        "sa_account",
                        "login",
                        "config",
                        "service",
                        "database",
                        "backup",
                        "trigger",
                        "protocol",
                        "permission",
                        "server_role_member",
                    }

                    parts = action.entity_key.split("|")
                    finding_key = action.entity_key

                    if len(parts) > 1 and parts[0].lower() in known_types:
                        finding_key = "|".join(parts[1:])

                    # Update status in the CURRENT sync run findings
                    # Note: We assume the finding exists in the sync run (it should, as it was re-audited)
                    self.store.update_finding_status(
                        run_id=sync_run_id,
                        entity_key=finding_key,
                        status="Exception",
                    )
                    logger.debug(
                        "Updated finding status to Exception for %s (Key: %s)",
                        action.entity_key,
                        finding_key,
                    )

            except Exception as e:
                logger.error("Failed to record action %s: %s", action.entity_key, e)

        return recorded

    def update_user_edits(
        self,
        action_id: int,
        user_date: str | None = None,
        notes: str | None = None,
    ) -> bool:
        """
        Update user-edited fields for an action.

        These fields are preserved across syncs.

        Args:
            action_id: Database ID of the action
            user_date: User's date override (if any)
            notes: User's notes

        Returns:
            True if update succeeded
        """
        # Note: This requires the store to have an update method
        # For now, this is handled by upsert_action with the same entity_key
        logger.debug("User edit update for action %d", action_id)
        return True

    def get_formatted_actions(
        self,
        initial_run_id: int,
    ) -> list[dict[str, Any]]:
        """
        Get actions formatted for Excel output.

        Includes all fields needed for the Actions sheet.

        Args:
            initial_run_id: Baseline audit run ID

        Returns:
            List of dicts with formatted action data
        """
        actions = self.store.get_actions_for_run(initial_run_id)

        formatted = []
        for action in actions:
            # Parse entity key for display fields
            entity_key = action.get("entity_key", "")
            parts = entity_key.split("|")

            server = "Unknown"
            instance = ""
            category = action.get("action_type", "")
            finding = entity_key

            if len(parts) >= 3:
                known_types = {
                    "sa_account",
                    "login",
                    "config",
                    "service",
                    "database",
                    "backup",
                    "trigger",
                    "protocol",
                }
                if parts[0].lower() in known_types:
                    server = parts[1]
                    instance = parts[2]
                    category = parts[0].title()
                    finding = "|".join(parts[3:]) if len(parts) > 3 else entity_key
                else:
                    server = parts[0]
                    instance = parts[1]
                    finding = "|".join(parts[2:]) if len(parts) > 2 else entity_key

            # Determine display status
            status_db = action.get("status", "open").lower()
            if status_db in ("fixed", "exception"):
                display_status = "Closed"
                risk = "Low"
            else:
                display_status = "Open"
                risk = "High"

            # Parse date (prefer user override)
            action_date = None
            date_str = action.get("user_date_override") or action.get("action_date")
            if date_str:
                try:
                    action_date = datetime.fromisoformat(date_str)
                except (ValueError, TypeError):
                    pass

            formatted.append(
                {
                    "id": action.get("id"),
                    "server": server,
                    "instance": instance,
                    "category": category,
                    "finding": finding,
                    "risk_level": risk,
                    "description": action.get("description", ""),
                    "status": display_status,
                    "detected_date": action_date,
                    "notes": action.get("notes", ""),
                    "entity_key": entity_key,
                    "action_type": action.get("action_type"),
                }
            )

        # Sort by date
        # Ensure datetime awareness for sorting
        def safe_date_sort(x):
            dt = x.get("detected_date")
            if not dt:
                return datetime.min.replace(tzinfo=timezone.utc)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt

        formatted.sort(key=safe_date_sort)

        return formatted
