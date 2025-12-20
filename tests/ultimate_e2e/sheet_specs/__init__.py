"""
Sheet Specifications Package.

Each sheet has its own spec file defining:
- Sheet name
- Entity type
- Writer method and sample data
- Editable columns
- Expected behaviors
"""

from .base import SheetSpec
from .all_specs import (
    ALL_SHEET_SPECS,
    get_spec_by_name,
    get_specs_with_exceptions,
    get_data_specs,
)

__all__ = [
    "SheetSpec",
    "ALL_SHEET_SPECS",
    "get_spec_by_name",
    "get_specs_with_exceptions",
    "get_data_specs",
]
