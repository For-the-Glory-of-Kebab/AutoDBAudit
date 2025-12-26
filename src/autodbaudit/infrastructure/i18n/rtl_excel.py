"""
RTL (Right-to-Left) Excel Support.

Provides utilities for generating RTL Excel sheets for Persian output.
Handles:
- Sheet direction
- Cell alignment
- Column order reversal (optional)
- Font application
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from openpyxl.worksheet.worksheet import Worksheet
from openpyxl.styles import Alignment, Font

from autodbaudit.infrastructure.i18n import Translator

if TYPE_CHECKING:
    from openpyxl.cell import Cell

logger = logging.getLogger(__name__)


def apply_rtl_to_worksheet(ws: Worksheet, translator: Translator) -> None:
    """
    Apply RTL settings to a worksheet.

    Args:
        ws: Worksheet to modify
        translator: Translator with language/font config
    """
    if not translator.is_rtl:
        return

    # Set sheet direction to RTL
    ws.sheet_view.rightToLeft = True

    logger.debug("Applied RTL to sheet: %s", ws.title)


def apply_rtl_to_cell(
    cell: Cell,
    translator: Translator,
    is_header: bool = False,
) -> None:
    """
    Apply RTL styling to a cell.

    Args:
        cell: Cell to style
        translator: Translator with font config
        is_header: Whether this is a header cell (uses heading font)
    """
    if not translator.is_rtl:
        return

    # Get font name
    font_name = translator.heading_font if is_header else translator.content_font

    # Apply RTL alignment - right align for RTL text
    current_align = cell.alignment or Alignment()
    cell.alignment = Alignment(
        horizontal="right",
        vertical=current_align.vertical or "center",
        wrap_text=current_align.wrap_text,
        text_rotation=current_align.text_rotation,
    )

    # Apply font
    current_font = cell.font or Font()
    cell.font = Font(
        name=font_name,
        size=current_font.size,
        bold=current_font.bold,
        italic=current_font.italic,
        color=current_font.color,
    )


def apply_rtl_to_header_row(
    ws: Worksheet,
    header_row: int,
    translator: Translator,
) -> None:
    """
    Apply RTL styling to entire header row.

    Args:
        ws: Worksheet
        header_row: Row number of headers (1-indexed)
        translator: Translator with font config
    """
    if not translator.is_rtl:
        return

    for cell in ws[header_row]:
        if cell.value:
            apply_rtl_to_cell(cell, translator, is_header=True)


def translate_headers_in_place(
    ws: Worksheet,
    header_row: int,
    translator: Translator,
) -> None:
    """
    Translate header cell values in place.

    Args:
        ws: Worksheet with headers
        header_row: Row number of headers (1-indexed)
        translator: Translator to use
    """
    for cell in ws[header_row]:
        if cell.value and isinstance(cell.value, str):
            cell.value = translator.header(cell.value)


def create_persian_font(
    translator: Translator,
    size: int = 11,
    bold: bool = False,
    is_header: bool = False,
) -> Font:
    """
    Create a Font object for Persian text.

    Args:
        translator: Translator with font config
        size: Font size
        bold: Whether to make bold
        is_header: Use heading font if True

    Returns:
        openpyxl Font object
    """
    font_name = translator.heading_font if is_header else translator.content_font
    return Font(name=font_name, size=size, bold=bold)
