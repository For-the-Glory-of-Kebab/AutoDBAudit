"""
Sheet Configuration for Sync Operations.

⚠️ DEPRECATION NOTICE:
This module exists for backward compatibility only.
The SINGLE SOURCE OF TRUTH is: autodbaudit.domain.sheet_registry

All new code should import from sheet_registry directly.
This module will be removed in a future version.

Migration:
    # Old (deprecated):
    from autodbaudit.application.sync.config import SHEET_CONFIGS

    # New (preferred):
    from autodbaudit.domain.sheet_registry import SHEET_REGISTRY, get_spec
"""

from __future__ import annotations

from autodbaudit.domain.sheet_registry import (
    SHEET_REGISTRY,
    SheetSpec,
    get_spec,
    get_all_trackable_sheets,
    get_editable_columns,
)


def get_sync_config(sheet_name: str) -> dict | None:
    """
    Get sync configuration for a sheet (DEPRECATED).

    Use sheet_registry.get_spec() instead.

    Returns dict with:
        - entity_type
        - key_cols (list)
        - editable_cols (dict)
    """
    spec = get_spec(sheet_name)
    if not spec:
        return None

    return {
        "entity_type": spec.entity_type,
        "key_cols": list(spec.key_columns),
        "editable_cols": dict(spec.editable_columns),
    }


def get_all_sync_configs() -> dict[str, dict]:
    """
    Get all sheet sync configurations (DEPRECATED).

    Use sheet_registry.get_all_trackable_sheets() instead.
    """
    configs = {}
    for spec in get_all_trackable_sheets():
        configs[spec.name] = get_sync_config(spec.name)
    return configs


# Re-export for compatibility
__all__ = [
    "SHEET_REGISTRY",
    "SheetSpec",
    "get_spec",
    "get_all_trackable_sheets",
    "get_editable_columns",
    "get_sync_config",
    "get_all_sync_configs",
]
