# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""``PdfTheme``: a tool's own font and colours for the frame, with the bundled font as fallback.

A paragraph whose text has characters the theme font lacks (but the bundled Plus Jakarta Sans has)
is set in the bundled font, in the same weight; only what neither font has becomes "?".
"""

import re
from dataclasses import dataclass, field
from html import unescape
from pathlib import Path

from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph

from .fonts import FONT, FONT_BOLD

_TAG = re.compile(r"<[^>]*>")
_coverage: dict[str, frozenset[int]] = {}


def covered(font_name: str) -> frozenset[int]:
    """Code points a registered TrueType font has (cached per font name)."""
    if font_name not in _coverage:
        _coverage[font_name] = frozenset(pdfmetrics.getFont(font_name).face.charToGlyph)
    return _coverage[font_name]


@dataclass(frozen=True)
class FontFamily:
    """The four registered reportlab font names of one family."""

    normal: str
    bold: str
    italic: str
    bold_italic: str

    def names(self) -> tuple[str, str, str, str]:
        return (self.normal, self.bold, self.italic, self.bold_italic)


BUNDLED_FAMILY = FontFamily(FONT, FONT_BOLD, FONT + "-Italic", FONT + "-BoldItalic")


def register_font_family(name: str, *, regular: str | Path, bold: str | Path | None = None,
                         italic: str | Path | None = None,
                         bold_italic: str | Path | None = None) -> FontFamily:
    """Register TrueType files as one family (``<b>``/``<i>`` in markup pick the right cut) and
    return its names for :class:`PdfTheme`. A missing cut falls back to the nearest one: italic to
    regular, bold italic to bold (or italic). Calling it again with the same name is a no-op."""
    files = {name: regular, f"{name}-Bold": bold, f"{name}-Italic": italic, f"{name}-BoldItalic": bold_italic}
    known = set(pdfmetrics.getRegisteredFontNames())
    for font_name, path in files.items():
        if path is not None and font_name not in known:
            pdfmetrics.registerFont(TTFont(font_name, str(path)))
    normal = name
    bold_name = f"{name}-Bold" if bold is not None else normal
    italic_name = f"{name}-Italic" if italic is not None else normal
    bold_italic_name = (f"{name}-BoldItalic" if bold_italic is not None
                        else bold_name if bold is not None else italic_name)
    pdfmetrics.registerFontFamily(name, normal=normal, bold=bold_name, italic=italic_name,
                                  boldItalic=bold_italic_name)
    return FontFamily(normal, bold_name, italic_name, bold_italic_name)


@dataclass(frozen=True)
class PdfTheme:
    """Font and colours of a :class:`~basicbar_pdf.PdfDocument`. The defaults are the frame's
    own look; colours are hex strings. ``heading`` None means the text colour."""

    fonts: FontFamily = BUNDLED_FAMILY
    text: str = "#000000"
    muted: str = "#666666"
    heading: str | None = None
    quote: str = "#444444"
    grid: str = "#c8c8c8"
    table_head: str = "#eeeeee"
    box_fill: str = "#f3f3f3"
    box_border: str = "#aaaaaa"
    footer: str = "#555555"
    _fallback_styles: dict = field(default_factory=dict, init=False, repr=False, compare=False, hash=False)

    @property
    def own_font(self) -> bool:
        """Whether the theme sets a font other than the bundled one."""
        return self.fonts != BUNDLED_FAMILY

    def safe(self, text) -> str:
        """Characters neither the theme font nor the bundled font has become "?"."""
        known = covered(self.fonts.normal) | covered(FONT) if self.own_font else covered(FONT)
        return "".join(c if c.isspace() or ord(c) in known else "?" for c in str(text))

    def lacks(self, markup: str) -> bool:
        """Whether the visible text of ``markup`` has characters the theme font lacks."""
        if not self.own_font:
            return False
        own = covered(self.fonts.normal)
        return any(not c.isspace() and ord(c) not in own for c in unescape(_TAG.sub("", markup)))

    def font_for(self, font_name: str, text: str) -> str:
        """``font_name`` (a cut of the theme family), or the bundled cut of the same weight when
        ``text`` (plain) has characters the theme font lacks."""
        if not self.own_font or not any(not c.isspace() and ord(c) not in covered(self.fonts.normal)
                                        for c in text):
            return font_name
        return _BUNDLED_BY_CUT.get(self._cut(font_name), FONT)

    def _cut(self, font_name: str) -> str:
        fonts = self.fonts
        # upright first: a family without italics maps italic to the upright name
        for cut, name in (("normal", fonts.normal), ("bold", fonts.bold),
                          ("italic", fonts.italic), ("bold_italic", fonts.bold_italic)):
            if font_name == name:
                return cut
        return "normal"

    def fallback_style(self, style: ParagraphStyle) -> ParagraphStyle:
        """``style`` set in the bundled font of the same weight (cached per style)."""
        key = id(style)
        cached = self._fallback_styles.get(key)
        if cached is not None and cached[0] is style:
            return cached[1]
        derived = ParagraphStyle(f"{style.name}-fallback", parent=style,
                                 fontName=_BUNDLED_BY_CUT.get(self._cut(style.fontName), FONT))
        self._fallback_styles[key] = (style, derived)
        return derived

    def paragraph(self, markup: str, style: ParagraphStyle, **kwargs) -> Paragraph:
        """A Paragraph of (already escaped) ``markup``, in the bundled font when the theme font
        lacks a character of it."""
        return Paragraph(markup, self.fallback_style(style) if self.lacks(markup) else style, **kwargs)


_BUNDLED_BY_CUT = dict(zip(("normal", "bold", "italic", "bold_italic"), BUNDLED_FAMILY.names()))

DEFAULT_THEME = PdfTheme()
