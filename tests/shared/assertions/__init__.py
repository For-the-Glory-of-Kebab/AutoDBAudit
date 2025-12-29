"""
Shared Assertions - Cross-suite verification utilities.

Both mock (ultimate_e2e) and real-DB tests import these.

Shallow assertions (legacy):
- ExcelAssertions, StateAssertions, StatsAssertions, ActionLogAssertions

Deep assertions (comprehensive):
- DeepExcelAssertions, DeepActionLogAssertions, DeepStateAssertions
- BaselineCapture, BaselineDelta
"""

# Legacy shallow assertions
from .excel import ExcelAssertions
from .state import StateAssertions
from .stats import StatsAssertions
from .action_log import ActionLogAssertions

# Deep comprehensive assertions
from .deep_excel import DeepExcelAssertions, RowData, CellStyle
from .deep_action_log import DeepActionLogAssertions, ActionLogEntry
from .deep_state import DeepStateAssertions, StateSnapshot, TransitionType
from .baseline import BaselineCapture, BaselineDelta, AuditBaseline, PROTECTED_ENTITIES

__all__ = [
    # Legacy
    "ExcelAssertions",
    "StateAssertions",
    "StatsAssertions",
    "ActionLogAssertions",
    # Deep
    "DeepExcelAssertions",
    "DeepActionLogAssertions",
    "DeepStateAssertions",
    "RowData",
    "CellStyle",
    "ActionLogEntry",
    "StateSnapshot",
    "TransitionType",
    "BaselineCapture",
    "BaselineDelta",
    "AuditBaseline",
    "PROTECTED_ENTITIES",
]
