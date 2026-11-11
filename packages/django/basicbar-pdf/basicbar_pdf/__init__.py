# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""PDF frame for downloadable documents of the -bar tools (reportlab, bundled Plus Jakarta Sans).

No Django dependency: user-visible labels (page footer, image placeholder) are parameters, so a
tool passes its own (lazy) gettext strings.
"""

from .document import PdfDocument
from .fonts import FONT, FONT_BOLD, safe_text
from .html import html_to_flowables, make_styles

__all__ = ["FONT", "FONT_BOLD", "PdfDocument", "html_to_flowables", "make_styles", "safe_text"]
