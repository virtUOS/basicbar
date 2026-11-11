# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Editor HTML (TipTap subset) to reportlab flowables, and the shared paragraph styles."""

import re
from html.parser import HTMLParser
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph

from .fonts import FONT, FONT_BOLD, safe_text

INLINE_TAGS = {"strong": "b", "b": "b", "em": "i", "i": "i", "u": "u", "s": "strike", "del": "strike",
               "strike": "strike"}
HEADINGS = {"h1": "h1", "h2": "h2", "h3": "h3"}
SKIP_CONTENT = {"script", "style"}
TABLE_TAGS = {"table", "thead", "tbody", "tfoot", "tr"}


def _markup(text: str) -> str:
    return escape(safe_text(text)).replace("\n", "<br/>")


def make_styles() -> dict:
    """Paragraph styles in the bundled font: normal, small, bold, muted, h1-h3, quote, cell, cell_head."""
    base = getSampleStyleSheet()["Normal"]
    normal = ParagraphStyle("n", parent=base, fontName=FONT, fontSize=10, leading=13.5, spaceAfter=3)
    styles = {
        "normal": normal,
        "small": ParagraphStyle("s", parent=normal, fontSize=8.5, leading=11),
        "bold": ParagraphStyle("b", parent=normal, fontName=FONT_BOLD),
        "muted": ParagraphStyle("m", parent=normal, fontSize=8.5, leading=11, textColor=colors.HexColor("#666666")),
        "h1": ParagraphStyle("h1", parent=normal, fontName=FONT_BOLD, fontSize=18, leading=22,
                             spaceBefore=4, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=normal, fontName=FONT_BOLD, fontSize=15, leading=18,
                             spaceBefore=14, spaceAfter=5),
        "h3": ParagraphStyle("h3", parent=normal, fontName=FONT_BOLD, fontSize=12, leading=15,
                             spaceBefore=8, spaceAfter=2),
        "quote": ParagraphStyle("q", parent=normal, leftIndent=10, textColor=colors.HexColor("#444444")),
        "cell": ParagraphStyle("c", parent=normal, fontSize=9, leading=11.5, spaceAfter=0),
        "cell_head": ParagraphStyle("ch", parent=normal, fontName=FONT_BOLD, fontSize=9, leading=11.5,
                                    spaceAfter=0),
    }
    return styles


def _has(styles, key) -> bool:
    try:
        styles[key]
        return True
    except KeyError:
        return False


class _HtmlToFlowables(HTMLParser):
    """Editor HTML (p, br, inline formatting, lists, headings, blockquote) to Paragraphs. Unknown
    tags are dropped, their text kept; the markup passed to reportlab is always balanced."""

    def __init__(self, styles, image_placeholder):
        super().__init__(convert_charrefs=True)
        self.image_placeholder = image_placeholder
        own = make_styles()
        # accept any mapping/stylesheet; keys it lacks fall back to the built-in styles
        self.styles = {key: (styles[key] if _has(styles, key) else own[key]) for key in own}
        self.out = []
        self.buf = ""
        self.open = []          # inline tags currently open (reportlab names)
        self.block = "normal"   # style key of the paragraph being built
        self.lists = []         # stack of [kind, counter]
        self.bullet = None
        self.hrefs = []
        self.skip = 0
        self.has_text = False
        self.cells = 0          # cells already seen in the current table row
        self.pre = 0

    # -- paragraph handling
    def _flush(self):
        if self.has_text:
            closing = "".join(f"</{t}>" for t in reversed(self.open))
            self.out.append(self._paragraph(self.buf + closing))
            # the bullet belongs to the first paragraph of the item only (TipTap: <li><p>..</p></li>)
            self.bullet = None
        self.buf = "".join(f"<{t}>" for t in self.open)
        self.has_text = False

    def _paragraph(self, markup):
        depth = len(self.lists)
        style = self.styles[self.block]
        if self.bullet is not None:
            style = ParagraphStyle("li", parent=style, leftIndent=12 * depth + 4, bulletIndent=12 * (depth - 1))
        try:
            return Paragraph(markup, style, bulletText=self.bullet)
        except Exception:  # never let one broken fragment kill the document
            plain = re.sub(r"<[^>]*>", "", markup.replace("<br/>", " "))  # already escaped
            return Paragraph(plain, style, bulletText=self.bullet)

    def handle_starttag(self, tag, attrs):
        if tag in SKIP_CONTENT:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in INLINE_TAGS:
            self.open.append(INLINE_TAGS[tag])
            self.buf += f"<{INLINE_TAGS[tag]}>"
        elif tag == "a":
            self.hrefs.append(dict(attrs).get("href") or "")
        elif tag == "br":
            self.buf += "<br/>"
        elif tag == "img":
            self.buf += escape(safe_text(self.image_placeholder))
            self.has_text = True
        elif tag in ("td", "th"):
            if self.cells:
                self.buf += " | "
            self.cells += 1
        elif tag in TABLE_TAGS:
            self._flush()
            self.cells = 0
        elif tag == "pre":
            self._flush()
            self.pre += 1
        elif tag in ("ul", "ol"):
            self._flush()
            self.lists.append([tag, 0])
        elif tag == "li":
            self._flush()
            if not self.lists:
                self.lists.append(["ul", 0])
            entry = self.lists[-1]
            entry[1] += 1
            self.bullet = f"{entry[1]}." if entry[0] == "ol" else "•"
        elif tag in HEADINGS:
            self._flush()
            self.block = HEADINGS[tag]
        elif tag == "blockquote":
            self._flush()
            self.block = "quote"
        elif tag in ("p", "div"):
            self._flush()

    def handle_endtag(self, tag):
        if tag in SKIP_CONTENT:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in INLINE_TAGS:
            name = INLINE_TAGS[tag]
            if name in self.open:
                # close down to the match, reopen the tags in between (keeps markup balanced)
                idx = len(self.open) - 1 - self.open[::-1].index(name)
                inner = self.open[idx + 1:]
                self.buf += "".join(f"</{t}>" for t in reversed(self.open[idx:]))
                self.buf += "".join(f"<{t}>" for t in inner)
                self.open = self.open[:idx] + inner
        elif tag == "a":
            if self.hrefs:
                href = self.hrefs.pop()
                if href:
                    self.buf += escape(safe_text(f" ({href})"))
        elif tag in ("ul", "ol"):
            self._flush()
            self.bullet = None
            if self.lists:
                self.lists.pop()
        elif tag in TABLE_TAGS or tag == "pre":
            self._flush()
            self.cells = 0
            if tag == "pre":
                self.pre = max(0, self.pre - 1)
        elif tag in ("li", "p", "div") or tag in HEADINGS or tag == "blockquote":
            self._flush()
            if tag in HEADINGS or tag == "blockquote":
                self.block = "normal"

    def handle_data(self, data):
        if self.skip:
            return
        if self.pre:
            self.buf += _markup(data)
            if data.strip():
                self.has_text = True
            return
        if not self.open and not self.buf.strip() and not data.strip():
            return
        self.buf += escape(safe_text(data))
        if data.strip():
            self.has_text = True

    def result(self):
        self.close()
        self._flush()
        return self.out


def html_to_flowables(html: str, styles, *, image_placeholder="[Image]") -> list:
    """Editor HTML to flowables. ``styles`` is any mapping/stylesheet; keys it lacks fall back to
    :func:`make_styles`. ``image_placeholder`` (str or lazy translation) stands in for ``<img>``."""
    parser = _HtmlToFlowables(styles, str(image_placeholder))
    parser.feed(html or "")
    return parser.result()
