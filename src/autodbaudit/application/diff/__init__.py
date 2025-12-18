"""
Diff module for comparing audit findings and entities.

This module provides pure functions for diffing:
- Findings between runs
- Entity mutations
- Exception changes

All diff functions use the domain state machine for transition classification.
"""

from autodbaudit.application.diff.findings_diff import (
    diff_findings,
    FindingsDiffResult,
    build_findings_map,
)

__all__ = [
    "diff_findings",
    "FindingsDiffResult",
    "build_findings_map",
]
