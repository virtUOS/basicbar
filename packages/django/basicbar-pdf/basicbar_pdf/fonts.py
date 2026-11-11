# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Bundled Plus Jakarta Sans (SIL OFL 1.1, see fonts/OFL.txt), registered once on import."""

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT = "PlusJakartaSans"
FONT_BOLD = FONT + "-Bold"
FONT_DIR = Path(__file__).resolve().parent / "fonts"
_FONT_FILES = {FONT: "Regular", FONT_BOLD: "Bold", FONT + "-Italic": "Italic", FONT + "-BoldItalic": "BoldItalic"}
_covered: set[int] = set()


def _register_fonts() -> None:
    """Register the bundled TTFs once (idempotent) and remember which code points the font has."""
    if _covered:
        return
    for name, style in _FONT_FILES.items():
        pdfmetrics.registerFont(TTFont(name, FONT_DIR / f"PlusJakartaSans-{style}.ttf"))
    pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT_BOLD, italic=FONT + "-Italic",
                                  boldItalic=FONT + "-BoldItalic")
    _covered.update(pdfmetrics.getFont(FONT).face.charToGlyph)


_register_fonts()


def safe_text(text) -> str:
    """Characters the bundled font lacks (Greek, Cyrillic, CJK, emoji, ...) become "?"."""
    return "".join(c if c.isspace() or ord(c) in _covered else "?" for c in str(text))
