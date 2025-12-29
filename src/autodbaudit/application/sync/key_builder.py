"""
Key Builder - Entity key normalization and construction.

Provides utilities for building stable entity keys from row data.
Uses the central sheet_registry for key column definitions.

Key Format:
    entity_type|server|instance|entity_parts...

Example:
    "backup|SQLPROD01|(Default)|MyDatabase"
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from autodbaudit.domain.sheet_registry import SheetSpec


def normalize_key(value: str) -> str:
    """
    Normalize a key value for consistent matching.

    - Lowercase
    - Strip whitespace
    - Remove non-ASCII (emojis/icons)
    - Replace multiple spaces with single
    """
    if not value:
        return ""

    # Remove non-ASCII (icons, emojis)
    clean = value.encode("ascii", "ignore").decode("ascii")

    # Lowercase and strip
    clean = clean.lower().strip()

    # Collapse multiple spaces
    clean = re.sub(r"\s+", " ", clean)

    return clean


def build_entity_key(
    entity_type: str,
    key_parts: list[str],
) -> str:
    """
    Build a full entity key from parts.

    Args:
        entity_type: Entity type (e.g., "backup", "service")
        key_parts: List of key column values

    Returns:
        Normalized key: "entity_type|part1|part2|..."
    """
    normalized = [normalize_key(entity_type)]
    for part in key_parts:
        normalized.append(normalize_key(part) or "(default)")

    return "|".join(normalized)


def build_key_from_row(
    spec: "SheetSpec",
    row_data: dict[str, str],
) -> str:
    """
    Build entity key from row data using sheet spec.

    Args:
        spec: SheetSpec with key_columns defined
        row_data: Dict mapping column name to value

    Returns:
        Full normalized entity key
    """
    parts = []
    for col in spec.key_columns:
        val = row_data.get(col, "")
        if col.lower() == "instance" and not val:
            val = "(Default)"
        parts.append(val)

    return build_entity_key(spec.entity_type, parts)


def parse_entity_key(key: str) -> tuple[str, list[str]]:
    """
    Parse entity key back into entity_type and parts.

    Args:
        key: Full entity key string

    Returns:
        Tuple of (entity_type, [parts...])
    """
    parts = key.split("|")
    if not parts:
        return "", []

    return parts[0], parts[1:]


def clean_key_value(val: str) -> str:
    """
    Clean key value by stripping non-ASCII characters (icons/emojis).
    Used to normalize keys that contain decoration icons in Excel.
    """
    if not val:
        return ""
    return str(val).encode("ascii", "ignore").decode("ascii").strip()
