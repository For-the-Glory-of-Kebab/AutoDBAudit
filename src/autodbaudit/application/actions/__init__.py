"""
Actions module for detecting and recording sync actions.

This module handles:
- Detecting what actions occurred during a sync
- Recording actions to the database (with deduplication)
- Formatting actions for Excel and CLI output
"""

from autodbaudit.application.actions.action_detector import (
    detect_all_actions,
    consolidate_actions,
)
from autodbaudit.application.actions.action_recorder import (
    ActionRecorder,
    should_record_action,
)

__all__ = [
    "detect_all_actions",
    "consolidate_actions",
    "ActionRecorder",
    "should_record_action",
]
