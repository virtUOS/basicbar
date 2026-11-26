# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""PDF frame for downloadable documents of the -bar tools (reportlab, bundled Plus Jakarta Sans,
optional theme with the tool's own font and colours).

No Django dependency: user-visible labels (page footer, image placeholder) are parameters, so a
tool passes its own (lazy) gettext strings.
"""

from .document import PdfDocument
from .fonts import FONT, FONT_BOLD, safe_text
from .html import html_to_flowables, make_styles
from .theme import BUNDLED_FAMILY, DEFAULT_THEME, FontFamily, PdfTheme, register_font_family

__all__ = ["BUNDLED_FAMILY", "DEFAULT_THEME", "FONT", "FONT_BOLD", "FontFamily", "PdfDocument", "PdfTheme",
           "html_to_flowables", "make_styles", "register_font_family", "safe_text"]
