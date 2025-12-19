"""
EntityKey - Canonical entity key class for consistent key format across all modules.

This is the single source of truth for entity key format in the sync engine.
All keys are normalized to lowercase for case-insensitive matching.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EntityKey:
    """
    Canonical entity key for consistent identification across all modules.

    Key format: entity_type|server|instance|identifier1|identifier2|...

    All parts are normalized to lowercase for case-insensitive matching.

    Examples:
        - backup|localhost|intheend|adventureworks|full
        - login|localhost|:1444|sa
        - config|localhost|bigbad2008|xp_cmdshell
    """

    entity_type: str
    server: str
    instance: str
    identifiers: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate key components."""
        if not self.entity_type:
            raise ValueError("entity_type cannot be empty")
        if not self.server:
            raise ValueError("server cannot be empty")

    @classmethod
    def from_parts(
        cls,
        entity_type: str,
        server: str,
        instance: str,
        *identifiers: str,
    ) -> EntityKey:
        """
        Build EntityKey from individual parts.

        All parts are normalized to lowercase.

        Args:
            entity_type: Type like 'backup', 'login', 'config'
            server: Server name
            instance: Instance name (use empty string for default)
            *identifiers: Additional identifying parts

        Returns:
            EntityKey instance
        """
        return cls(
            entity_type=str(entity_type).lower().strip(),
            server=str(server).lower().strip(),
            instance=str(instance).lower().strip() if instance else "",
            identifiers=tuple(str(i).lower().strip() for i in identifiers),
        )

    @classmethod
    def from_string(cls, key_string: str) -> EntityKey:
        """
        Parse EntityKey from pipe-delimited string.

        Expected format: entity_type|server|instance|id1|id2|...

        Args:
            key_string: Pipe-delimited key string

        Returns:
            EntityKey instance
        """
        if not key_string:
            raise ValueError("key_string cannot be empty")

        parts = key_string.split("|")

        if len(parts) < 2:
            raise ValueError(f"Invalid key format, need at least 2 parts: {key_string}")

        entity_type = parts[0].lower().strip()
        server = parts[1].lower().strip() if len(parts) > 1 else ""
        instance = parts[2].lower().strip() if len(parts) > 2 else ""
        identifiers = tuple(p.lower().strip() for p in parts[3:])

        return cls(
            entity_type=entity_type,
            server=server,
            instance=instance,
            identifiers=identifiers,
        )

    @classmethod
    def from_finding_key(
        cls,
        entity_type: str,
        finding_key: str,
    ) -> EntityKey:
        """
        Parse EntityKey from a finding entity_key (which lacks entity_type prefix).

        Finding keys have format: server|instance|id1|id2|...

        Args:
            entity_type: The entity type to use
            finding_key: The finding's entity_key (without type prefix)

        Returns:
            EntityKey instance
        """
        if not finding_key:
            raise ValueError("finding_key cannot be empty")

        parts = finding_key.split("|")

        server = parts[0].lower().strip() if len(parts) > 0 else ""
        instance = parts[1].lower().strip() if len(parts) > 1 else ""
        identifiers = tuple(p.lower().strip() for p in parts[2:])

        return cls(
            entity_type=entity_type.lower().strip(),
            server=server,
            instance=instance,
            identifiers=identifiers,
        )

    def to_string(self) -> str:
        """
        Convert to canonical lowercase pipe-delimited string.

        Returns:
            String like 'backup|localhost|intheend|adventureworks|full'
        """
        parts = [self.entity_type, self.server, self.instance]
        parts.extend(self.identifiers)
        return "|".join(parts)

    def to_finding_key(self) -> str:
        """
        Convert to finding key format (without entity_type prefix).

        Returns:
            String like 'localhost|intheend|adventureworks|full'
        """
        parts = [self.server, self.instance]
        parts.extend(self.identifiers)
        return "|".join(parts)

    def matches(self, other: EntityKey | str) -> bool:
        """
        Case-insensitive comparison with another EntityKey or string.

        Args:
            other: EntityKey or pipe-delimited string to compare

        Returns:
            True if keys match (case-insensitive)
        """
        if isinstance(other, str):
            try:
                other = EntityKey.from_string(other)
            except ValueError:
                return False

        return self.to_string() == other.to_string()

    def matches_finding_key(
        self, finding_key: str, entity_type: str | None = None
    ) -> bool:
        """
        Check if this EntityKey matches a finding key (which lacks entity_type).

        Args:
            finding_key: The finding's entity_key (server|instance|...)
            entity_type: Optional entity type to verify (if provided, must match)

        Returns:
            True if the finding key matches (ignoring entity_type prefix)
        """
        if entity_type and self.entity_type != entity_type.lower():
            return False

        return self.to_finding_key() == finding_key.lower().strip()

    def __str__(self) -> str:
        return self.to_string()

    def __repr__(self) -> str:
        return f"EntityKey({self.to_string()})"

    def __hash__(self) -> int:
        return hash(self.to_string())

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, EntityKey):
            return self.to_string() == other.to_string()
        if isinstance(other, str):
            return self.matches(other)
        return False


def normalize_key_string(key_string: str) -> str:
    """
    Normalize a key string to lowercase.

    Utility function for quick normalization without creating EntityKey.

    Args:
        key_string: Any pipe-delimited key string

    Returns:
        Lowercase version of the key
    """
    if not key_string:
        return ""
    return "|".join(p.lower().strip() for p in key_string.split("|"))


def keys_match(key1: str, key2: str) -> bool:
    """
    Check if two key strings match (case-insensitive).

    Utility function for quick comparison.

    Args:
        key1: First key string
        key2: Second key string

    Returns:
        True if keys match (case-insensitive)
    """
    return normalize_key_string(key1) == normalize_key_string(key2)


def finding_key_to_annotation_key(entity_type: str, finding_key: str) -> str:
    """
    Convert a finding key to annotation key format.

    Finding key: server|instance|id1|id2
    Annotation key: entity_type|server|instance|id1|id2

    Args:
        entity_type: The entity type prefix
        finding_key: The finding's entity_key

    Returns:
        Annotation key string (lowercase)
    """
    entity_type = entity_type.lower().strip()
    finding_key = normalize_key_string(finding_key)
    return f"{entity_type}|{finding_key}"


def annotation_key_to_finding_key(annotation_key: str) -> tuple[str, str]:
    """
    Extract entity_type and finding_key from annotation key.

    Annotation key: entity_type|server|instance|id1|id2
    Returns: (entity_type, server|instance|id1|id2)

    Args:
        annotation_key: The annotation's full key

    Returns:
        Tuple of (entity_type, finding_key)
    """
    parts = annotation_key.split("|", 1)
    if len(parts) < 2:
        return parts[0].lower(), ""
    return parts[0].lower(), parts[1].lower()
