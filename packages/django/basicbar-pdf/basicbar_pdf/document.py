# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""``PdfDocument``: collects flowables and renders an A4 document with a numbered footer."""

from collections.abc import Callable, Iterable, Sequence
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape as _landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm as MM
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import HRFlowable, KeepTogether, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus.frames import Frame

from .html import _markup, html_to_flowables, make_styles
from .theme import DEFAULT_THEME, PdfTheme

PAGE_LABEL = "Page %(page)s of %(pages)s"
GRID = colors.HexColor(DEFAULT_THEME.grid)  # kept for tools that imported it; the theme decides
# SimpleDocTemplate's frame keeps reportlab's default padding inside the margins (top and bottom).
_FRAME_PADDING = Frame(0, 0, 100, 100).topPadding + Frame(0, 0, 100, 100).bottomPadding


def _numbered_canvas(footer_left: str, page_label: str, margin: float, theme: PdfTheme):
    left = theme.safe(footer_left)

    def draw(c, x, text, right=False):
        c.setFont(theme.font_for(theme.fonts.normal, text), 8)
        (c.drawRightString if right else c.drawString)(x, 10 * MM, text)

    class NumberedCanvas(canvas.Canvas):
        """Two passes: the page count is known only after the last page."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._pages = []

        def showPage(self):
            self._pages.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            count = len(self._pages)
            for state in self._pages:
                self.__dict__.update(state)
                width, _height = self._pagesize
                self.setFillColor(colors.HexColor(theme.footer))
                draw(self, margin, left)
                draw(self, width - margin, theme.safe(page_label % {"page": self._pageNumber, "pages": count}),
                     right=True)
                super().showPage()
            super().save()

    return NumberedCanvas


class PdfDocument:
    """Collects flowables and renders an A4 document (portrait or landscape) with a footer:
    ``footer_left`` on the left, "Page x of y" on the right.

    ``page_label`` and ``image_placeholder`` are the only user-visible strings of the frame; pass
    the tool's translations (``gettext_lazy`` works — they are resolved when used). All text is
    escaped; characters the bundled font lacks become "?" (:func:`safe_text`).

    ``theme`` (:class:`PdfTheme`) sets the tool's own font and colours; a paragraph the theme font
    cannot set falls back to the bundled font, and only characters neither font has become "?".
    """

    def __init__(self, title: str, *, footer_left: str = "", author: str = "", landscape: bool = False,
                 margin_mm: float = 20, page_label=PAGE_LABEL, image_placeholder="[Image]",
                 compress: bool = True, theme: PdfTheme | None = None):
        self.title = title
        self.author = author
        self.footer_left = footer_left
        self.pagesize = _landscape(A4) if landscape else A4
        self.margin = margin_mm * MM
        self.bottom = max(self.margin - 2 * MM, 15 * MM)  # room for the footer at 10 mm
        self.page_label = page_label
        self.image_placeholder = image_placeholder
        self.compress = compress
        self.theme = theme or DEFAULT_THEME
        self.styles = make_styles(self.theme)
        self._story: list = []

    @property
    def usable_width(self) -> float:
        """Width between the side margins in points (for ``col_widths``)."""
        return self.pagesize[0] - 2 * self.margin

    @property
    def usable_height(self) -> float:
        """Height a flowable may take on one page in points: between the margins, less the frame's
        own padding. Anything taller (a table row, a one-cell box) cannot be placed."""
        return self.pagesize[1] - self.margin - self.bottom - _FRAME_PADDING

    def _para(self, text: str, style: ParagraphStyle, **kwargs):
        return self.theme.paragraph(_markup(text, self.theme), style, **kwargs)

    def _add(self, *flowables):
        self._story.extend(flowables)

    def add(self, *flowables):
        """Escape hatch: append raw reportlab flowables."""
        self._add(*flowables)

    def heading(self, text: str, level: int = 1):
        self._add(self._para(text, self.styles[f"h{min(max(level, 1), 3)}"]))

    def paragraph(self, text: str, *, style: str = "normal"):
        self._add(self._para(text, self.styles[style]))

    def rich(self, html: str):
        """Editor HTML (paragraphs, inline formatting, lists, headings, quotes, links)."""
        self._add(*html_to_flowables(html, self.styles, image_placeholder=self.image_placeholder,
                                     theme=self.theme))

    def bullets(self, items: list[str]):
        style = ParagraphStyle("bl", parent=self.styles["normal"], leftIndent=16, bulletIndent=4)
        for item in items:
            self._add(self._para(item, style, bulletText="•"))

    def auto_widths(self, rows: Sequence[Sequence[str]], *, header: bool = True) -> list[float]:
        """Column widths for ``rows``: each column at least as wide as its longest header word and
        its longest value (no value is broken mid-word); the remaining width is shared evenly, or
        everything shrinks proportionally when the page is too narrow."""
        font_size = self.styles["cell"].fontSize
        bold = self.styles["cell_head"].fontName
        need = []
        for col in range(max((len(row) for row in rows), default=0)):
            widths = [0.0]
            for i, row in enumerate(rows):
                if col >= len(row):
                    continue
                cell = self.theme.safe(row[col])
                font = self.theme.font_for(bold, cell)
                if header and i == 0:
                    widths += [stringWidth(word, font, font_size) for word in cell.split()]
                else:
                    widths += [stringWidth(line, font, font_size) for line in cell.split("\n")]
            need.append(max(widths) + 8)  # cell padding left + right
        if not need:
            return []
        usable = self.usable_width
        extra = usable - sum(need)
        if extra >= 0:
            return [w + extra / len(need) for w in need]
        return [w * usable / sum(need) for w in need]

    def table(self, rows: list[list[str]], *, header: bool = True,
              col_widths: list[float] | str | None = None, align_right_from: int | None = None,
              strong_rows: Iterable[int] = ()):
        """A grid table; the header row repeats on every page.

        ``col_widths``: points per column, ``"auto"`` (:meth:`auto_widths`) or None (reportlab).
        ``align_right_from``: columns from this index on are right-aligned (numbers).
        ``strong_rows``: row indexes (counting the header as 0) set in bold, e.g. totals.
        """
        if not rows:
            return
        if col_widths == "auto":
            col_widths = self.auto_widths(rows, header=header)
        strong = set(strong_rows)
        styles = {}

        def cell_style(i: int, j: int) -> ParagraphStyle:
            bold = (header and i == 0) or i in strong
            right = align_right_from is not None and j >= align_right_from
            key = (bold, right)
            if key not in styles:
                base = self.styles["cell_head" if bold else "cell"]
                styles[key] = ParagraphStyle(f"cell{int(bold)}{int(right)}", parent=base,
                                             alignment=TA_RIGHT) if right else base
            return styles[key]

        data = [[self._para(cell, cell_style(i, j)) for j, cell in enumerate(row)]
                for i, row in enumerate(rows)]
        table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
        style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor(self.theme.grid)),
                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(self.theme.table_head)))
        table.setStyle(TableStyle(style))
        self._add(table, Spacer(1, 2 * MM))

    def rule(self):
        """Thin horizontal separator line."""
        self._add(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor(self.theme.grid),
                             spaceBefore=2 * MM, spaceAfter=2 * MM))

    def spacer(self, mm: float = 3):
        self._add(Spacer(1, mm * MM))

    def _collect(self, builder: Callable[["PdfDocument"], None]) -> list:
        outer, self._story = self._story, []
        try:
            builder(self)
            return self._story
        finally:
            self._story = outer

    def keep_together(self, builder: Callable[["PdfDocument"], None]):
        """Everything ``builder`` adds stays on one page if it fits (e.g. a heading with its table)."""
        self._add(KeepTogether(self._collect(builder)))

    def box(self, builder: Callable[["PdfDocument"], None]):
        """Light grey framed block. Rendered as a one-cell table, so it cannot split across pages;
        a block taller than a page is added unframed instead."""
        inner = self._collect(builder)
        box = Table([[inner]], colWidths=[self.usable_width])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(self.theme.box_fill)),
                                 ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor(self.theme.box_border)),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                 ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        # measured with its own padding: a one-cell table cannot split across pages
        if box.wrap(self.usable_width, self.pagesize[1])[1] > self.usable_height:
            self._add(*inner, Spacer(1, 2 * MM))
            return
        self._add(box, Spacer(1, 2 * MM))

    def render(self) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=self.pagesize, leftMargin=self.margin, rightMargin=self.margin,
                                topMargin=self.margin, bottomMargin=self.bottom, title=self.theme.safe(self.title),
                                author=self.theme.safe(self.author), pageCompression=1 if self.compress else 0)
        doc.build(list(self._story),
                  canvasmaker=_numbered_canvas(self.footer_left, str(self.page_label), self.margin, self.theme))
        return buffer.getvalue()
