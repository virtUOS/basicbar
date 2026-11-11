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
from reportlab.platypus import HRFlowable, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .fonts import FONT, FONT_BOLD, safe_text
from .html import _markup, html_to_flowables, make_styles

PAGE_LABEL = "Page %(page)s of %(pages)s"
GRID = colors.HexColor("#c8c8c8")


def _numbered_canvas(footer_left: str, page_label: str, margin: float):
    left = safe_text(footer_left)

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
                self.setFont(FONT, 8)
                self.setFillColor(colors.HexColor("#555555"))
                self.drawString(margin, 10 * MM, left)
                self.drawRightString(width - margin, 10 * MM,
                                     safe_text(page_label % {"page": self._pageNumber, "pages": count}))
                super().showPage()
            super().save()

    return NumberedCanvas


class PdfDocument:
    """Collects flowables and renders an A4 document (portrait or landscape) with a footer:
    ``footer_left`` on the left, "Page x of y" on the right.

    ``page_label`` and ``image_placeholder`` are the only user-visible strings of the frame; pass
    the tool's translations (``gettext_lazy`` works — they are resolved when used). All text is
    escaped; characters the bundled font lacks become "?" (:func:`safe_text`).
    """

    def __init__(self, title: str, *, footer_left: str = "", author: str = "", landscape: bool = False,
                 margin_mm: float = 20, page_label=PAGE_LABEL, image_placeholder="[Image]",
                 compress: bool = True):
        self.title = title
        self.author = author
        self.footer_left = footer_left
        self.pagesize = _landscape(A4) if landscape else A4
        self.margin = margin_mm * MM
        self.bottom = max(self.margin - 2 * MM, 15 * MM)  # room for the footer at 10 mm
        self.page_label = page_label
        self.image_placeholder = image_placeholder
        self.compress = compress
        self.styles = make_styles()
        self._story: list = []

    @property
    def usable_width(self) -> float:
        """Width between the side margins in points (for ``col_widths``)."""
        return self.pagesize[0] - 2 * self.margin

    def _add(self, *flowables):
        self._story.extend(flowables)

    def add(self, *flowables):
        """Escape hatch: append raw reportlab flowables."""
        self._add(*flowables)

    def heading(self, text: str, level: int = 1):
        self._add(Paragraph(_markup(text), self.styles[f"h{min(max(level, 1), 3)}"]))

    def paragraph(self, text: str, *, style: str = "normal"):
        self._add(Paragraph(_markup(text), self.styles[style]))

    def rich(self, html: str):
        """Editor HTML (paragraphs, inline formatting, lists, headings, quotes, links)."""
        self._add(*html_to_flowables(html, self.styles, image_placeholder=self.image_placeholder))

    def bullets(self, items: list[str]):
        style = ParagraphStyle("bl", parent=self.styles["normal"], leftIndent=16, bulletIndent=4)
        for item in items:
            self._add(Paragraph(_markup(item), style, bulletText="•"))

    def auto_widths(self, rows: Sequence[Sequence[str]], *, header: bool = True) -> list[float]:
        """Column widths for ``rows``: each column at least as wide as its longest header word and
        its longest value (no value is broken mid-word); the remaining width is shared evenly, or
        everything shrinks proportionally when the page is too narrow."""
        font_size = self.styles["cell"].fontSize
        need = []
        for col in range(max((len(row) for row in rows), default=0)):
            widths = [0.0]
            for i, row in enumerate(rows):
                if col >= len(row):
                    continue
                cell = safe_text(row[col])
                if header and i == 0:
                    widths += [stringWidth(word, FONT_BOLD, font_size) for word in cell.split()]
                else:
                    widths += [stringWidth(line, FONT_BOLD, font_size) for line in cell.split("\n")]
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

        data = [[Paragraph(_markup(cell), cell_style(i, j)) for j, cell in enumerate(row)]
                for i, row in enumerate(rows)]
        table = Table(data, colWidths=col_widths, repeatRows=1 if header else 0)
        style = [("VALIGN", (0, 0), (-1, -1), "TOP"),
                 ("GRID", (0, 0), (-1, -1), 0.25, GRID),
                 ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if header:
            style.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eeeeee")))
        table.setStyle(TableStyle(style))
        self._add(table, Spacer(1, 2 * MM))

    def rule(self):
        """Thin horizontal separator line."""
        self._add(HRFlowable(width="100%", thickness=0.5, color=GRID, spaceBefore=2 * MM, spaceAfter=2 * MM))

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
        width, height = self.pagesize
        box = Table([[inner]], colWidths=[self.usable_width])
        if box.wrap(self.usable_width, height)[1] > height - self.margin - self.bottom - 4 * MM:
            self._add(*inner, Spacer(1, 2 * MM))
            return
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f3f3f3")),
                                 ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#aaaaaa")),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                                 ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        self._add(box, Spacer(1, 2 * MM))

    def render(self) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=self.pagesize, leftMargin=self.margin, rightMargin=self.margin,
                                topMargin=self.margin, bottomMargin=self.bottom, title=safe_text(self.title),
                                author=safe_text(self.author), pageCompression=1 if self.compress else 0)
        doc.build(list(self._story),
                  canvasmaker=_numbered_canvas(self.footer_left, str(self.page_label), self.margin))
        return buffer.getvalue()
