"""
Translator - Main i18n interface.

Provides unified access to all translations.
Supports fallback to English if translation missing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from autodbaudit.infrastructure.i18n.sheets import SHEET_NAMES
from autodbaudit.infrastructure.i18n.headers import ALL_HEADERS
from autodbaudit.infrastructure.i18n.dropdowns import (
    STATUS_VALUES,
    RISK_LEVELS,
    CHANGE_TYPES,
    CHANGE_TYPE_OPTIONS,
    ACTION_CATEGORIES,
    REVIEW_STATUS,
    BOOLEAN_VALUES,
)
from autodbaudit.infrastructure.i18n.cover import (
    COVER_PAGE,
    COMMON_PHRASES,
    ALL_COVER_TEXT,
)

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = ("en", "fa")


@dataclass
class FontConfig:
    """Font configuration for a language."""

    heading_font: str
    content_font: str
    is_rtl: bool


# Font configurations per language
FONT_CONFIGS = {
    "en": FontConfig(
        heading_font="Calibri",
        content_font="Calibri",
        is_rtl=False,
    ),
    "fa": FontConfig(
        heading_font="IRTitr",
        content_font="IRNazanin",
        is_rtl=True,
    ),
}


class Translator:
    """
    Unified translator for i18n.

    Usage:
        t = Translator("fa")
        t.sheet("Instances")  # "نمونه‌ها"
        t.header("Server")    # "سرور"
        t.status("PASS")      # "تأیید"
    """

    def __init__(self, lang: str = "en") -> None:
        """Initialize translator for given language."""
        if lang not in SUPPORTED_LANGUAGES:
            logger.warning("Unsupported language '%s', falling back to 'en'", lang)
            lang = "en"

        self.lang = lang
        self.font_config = FONT_CONFIGS.get(lang, FONT_CONFIGS["en"])
        self._is_persian = lang == "fa"

    @property
    def is_rtl(self) -> bool:
        """Whether this language is right-to-left."""
        return self.font_config.is_rtl

    @property
    def heading_font(self) -> str:
        """Font for headings."""
        return self.font_config.heading_font

    @property
    def content_font(self) -> str:
        """Font for content."""
        return self.font_config.content_font

    def sheet(self, name: str) -> str:
        """Translate sheet name."""
        if not self._is_persian:
            return name
        return SHEET_NAMES.get(name, name)

    def header(self, name: str) -> str:
        """Translate column header."""
        if not self._is_persian:
            return name
        return ALL_HEADERS.get(name, name)

    def status(self, value: str) -> str:
        """Translate status value (PASS/FAIL/WARN)."""
        if not self._is_persian:
            return value
        return STATUS_VALUES.get(value, value)

    def risk(self, level: str) -> str:
        """Translate risk level."""
        if not self._is_persian:
            return level
        return RISK_LEVELS.get(level, level)

    def change_type(self, ctype: str) -> str:
        """Translate change type."""
        if not self._is_persian:
            return ctype
        # First check full option with icon
        if ctype in CHANGE_TYPE_OPTIONS:
            return CHANGE_TYPE_OPTIONS[ctype]
        # Then check plain value
        return CHANGE_TYPES.get(ctype, ctype)

    def category(self, cat: str) -> str:
        """Translate action category."""
        if not self._is_persian:
            return cat
        return ACTION_CATEGORIES.get(cat, cat)

    def review_status(self, status: str) -> str:
        """Translate review status."""
        if not self._is_persian:
            return status
        return REVIEW_STATUS.get(status, status)

    def boolean(self, value: str) -> str:
        """Translate boolean display value."""
        if not self._is_persian:
            return value
        return BOOLEAN_VALUES.get(value, value)

    def cover(self, key: str) -> str:
        """Get cover page text by key."""
        if not self._is_persian:
            # Return English defaults
            return key.replace("_", " ").title()
        return COVER_PAGE.get(key, key)

    def phrase(self, key: str) -> str:
        """Get common phrase by key."""
        if not self._is_persian:
            return key.replace("_", " ").title()
        return COMMON_PHRASES.get(key, key)

    def dropdown_options(self, dropdown_type: str) -> list[str]:
        """
        Get translated dropdown options.

        Args:
            dropdown_type: One of 'risk', 'change_type', 'category', 'review_status'

        Returns:
            List of translated option strings
        """
        mapping = {
            "risk": RISK_LEVELS,
            "change_type": CHANGE_TYPE_OPTIONS,
            "category": ACTION_CATEGORIES,
            "review_status": REVIEW_STATUS,
        }

        source = mapping.get(dropdown_type, {})

        if not self._is_persian:
            return list(source.keys())
        return list(source.values())

    def text(self, text: str) -> str:
        """
        Translate any UI text (cover page, labels, etc.).

        Searches ALL_COVER_TEXT for exact match.
        Returns original if not found.
        """
        if not self._is_persian:
            return text
        return ALL_COVER_TEXT.get(text, text)


def get_translator(lang: str = "en") -> Translator:
    """Factory function to get a translator."""
    return Translator(lang)
