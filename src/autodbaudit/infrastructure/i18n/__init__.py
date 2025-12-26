"""
Internationalization (i18n) Package.

Provides translations for Excel report generation.
Organized by category for easy maintenance.

Usage:
    from autodbaudit.infrastructure.i18n import get_translator

    t = get_translator("fa")  # Persian
    t.sheet_name("Instances")  # Returns "نمونه‌ها"
"""

from autodbaudit.infrastructure.i18n.translator import (
    Translator,
    get_translator,
    SUPPORTED_LANGUAGES,
)

__all__ = [
    "Translator",
    "get_translator",
    "SUPPORTED_LANGUAGES",
]
