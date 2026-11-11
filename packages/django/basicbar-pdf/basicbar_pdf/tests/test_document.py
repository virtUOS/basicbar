# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""The PDF frame: rendering, fonts, HTML conversion, robustness, layout options."""

import unittest


class PdfFrameTests(unittest.TestCase):
    """The generic reportlab frame used for downloadable documents."""

    RICH = ('<p>Eins <strong>fett</strong></p><ul><li>A</li><li>B</li></ul><ol><li>X</li></ol>'
            '<p><a href="https://x.org">Link</a> 😀 αβ</p>')

    def _texts(self, data):
        from io import BytesIO

        from pypdf import PdfReader
        return [page.extract_text() for page in PdfReader(BytesIO(data)).pages]

    def test_safe_text_replaces_unencodable_characters(self):
        from basicbar_pdf import safe_text
        self.assertEqual(safe_text("a😀"), "a?")
        self.assertEqual(safe_text("Grüße „x“ – ok"), "Grüße „x“ – ok")
        self.assertEqual(safe_text("αβ\n x"), "??\n x")

    def test_extended_latin_renders_with_bundled_font(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t", footer_left="Dvořák")
        doc.paragraph("Şahin Łukasz Dvořák → € ğ ı ß")
        doc.rich("<p><b>Şahin</b> <i>Łukasz</i> Greek αβ emoji 😀</p>")
        data = doc.render()
        text = "\n".join(self._texts(data))
        for needle in ("Şahin Łukasz Dvořák → € ğ ı ß", "Greek ?? emoji ?"):
            self.assertIn(needle, text)
        self.assertIn(b"PlusJakartaSans", data)

    def test_render_document_with_all_flowables(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("Titel", footer_left="Links", page_label="Seite %(page)s von %(pages)s")
        doc.heading("Überschrift")
        doc.heading("Unter", level=2)
        for style in ("normal", "small", "bold", "muted"):
            doc.paragraph(f"Absatz {style} <b>&", style=style)
        doc.rich(self.RICH)
        doc.bullets(["Punkt 1", "Punkt 2"])
        doc.table([["Kopf", "Wert"], ["a", "1"]], col_widths=[40, 40])
        doc.spacer()
        doc.keep_together(lambda d: (d.paragraph("zusammen"), d.paragraph("bleibt")))
        doc.box(lambda d: d.paragraph("Siegelblock"))
        for i in range(200):
            doc.paragraph(f"Zeile {i}")
        data = doc.render()
        self.assertTrue(data.startswith(b"%PDF"))
        pages = self._texts(data)
        self.assertGreater(len(pages), 1)
        text = "\n".join(pages)
        for needle in ("fett", "A", "B", "X", "Link", "https://x.org", "Siegelblock", "Punkt 2", "Links"):
            self.assertIn(needle, text)
        self.assertIn("Seite 1 von", pages[0])
        self.assertIn(f"Seite {len(pages)} von {len(pages)}", pages[-1])

    def test_default_english_footer(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("T")
        doc.paragraph("x")
        self.assertIn("Page 1 of 1", self._texts(doc.render())[0])

    def test_html_to_flowables_survives_messy_html(self):
        from reportlab.lib.styles import getSampleStyleSheet

        from basicbar_pdf import html_to_flowables
        styles = getSampleStyleSheet()
        messy = ('<h1>H</h1><blockquote>Zitat</blockquote><p><b>a<i>b</b>c</i> <u>u</u> <s>s</s> <del>d</del></p>'
                 '<ul><li>eins<ul><li>innen</li></ul></li></ul><div><span>lose</span></div>'
                 '<script>x</script><p>1 < 2 & 3</p></b></p><br>Rest')
        flowables = html_to_flowables(messy, styles)
        self.assertTrue(flowables)
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("T")
        doc.rich(messy)
        text = "\n".join(self._texts(doc.render()))
        for needle in ("Zitat", "innen", "lose", "Rest", "1 < 2 & 3"):
            self.assertIn(needle, text)

    def test_tiptap_list_items_keep_bullet_and_numbers(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("T")
        doc.rich("<ul><li><p>Alpha</p></li></ul><ol><li><p>Xaver</p></li><li><p>Yvonne</p></li></ol>"
                 "<p><b></b></p>")
        text = "\n".join(self._texts(doc.render()))
        # the bullet glyph is extracted as U+2022 or a control char depending on the font encoding
        self.assertRegex(text, "[\u2022\x7f]\\s*Alpha")
        self.assertRegex(text, r"1\.\s*Xaver")
        self.assertRegex(text, r"2\.\s*Yvonne")


class PdfFrameRobustnessTests(unittest.TestCase):
    """Inputs that used to hang or crash the render, and rich() fallbacks."""

    _texts = PdfFrameTests._texts

    def _render_guarded(self, doc, seconds=20):
        import signal

        def boom(*_):
            raise AssertionError("PDF render hangs")
        old = signal.signal(signal.SIGALRM, boom)
        signal.alarm(seconds)
        try:
            return doc.render()
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)

    def test_heading_taller_than_a_page_does_not_hang(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t")
        doc.heading("big " * 700, 2)
        doc.paragraph("danach")
        text = "\n".join(self._texts(self._render_guarded(doc)))
        self.assertIn("danach", text)

    def test_rich_heading_taller_than_a_page_does_not_hang(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t")
        doc.rich("<h1>" + "word " * 800 + "</h1><p>danach</p>")
        text = "\n".join(self._texts(self._render_guarded(doc)))
        self.assertIn("danach", text)

    def test_multiline_headings_do_not_hang(self):
        from basicbar_pdf import PdfDocument
        for build in (lambda d: d.heading("x\n" * 40, 1),
                      lambda d: d.heading("\n" * 299, 1),
                      lambda d: d.rich("<h1>" + "<br>" * 400 + "x</h1>"),
                      lambda d: d.heading("big " * 700, 3)):
            doc = PdfDocument("t")
            build(doc)
            self.assertTrue(self._render_guarded(doc).startswith(b"%PDF"))

    def test_rich_img_table_and_pre(self):
        from basicbar_pdf import PdfDocument
        html = ('<p>vor <img src="x.png"> nach</p>'
                "<table><tr><td>A1</td><td>B1</td></tr><tr><td>A2</td><td>B2</td></tr></table>"
                "<pre>zeile1\nzeile2</pre>")
        doc = PdfDocument("t", image_placeholder="[Bild]")
        doc.rich(html)
        text = "\n".join(self._texts(doc.render()))
        self.assertIn("[Bild]", text)
        self.assertIn("A1 | B1", text)
        self.assertIn("A2 | B2", text)
        self.assertRegex(text, r"zeile1\s*\nzeile2")
        doc2 = PdfDocument("t")
        doc2.rich('<img src="x.png">')
        self.assertIn("[Image]", "\n".join(self._texts(doc2.render())))

    def test_box_taller_than_a_page_falls_back(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t")
        doc.box(lambda d: [d.paragraph(f"Boxzeile {i}") for i in range(80)])
        text = "\n".join(self._texts(self._render_guarded(doc)))
        self.assertIn("Boxzeile 79", text)


class LazyLabel:
    """Stands in for a gettext_lazy proxy: only str() resolves it."""

    def __init__(self, text):
        self.text = text

    def __str__(self):
        return self.text


class PdfLayoutOptionTests(unittest.TestCase):
    """Options added for tools beyond abstimmbar (kalkulierbar's landscape number tables)."""

    _texts = PdfFrameTests._texts

    def test_landscape_page_size_and_author(self):
        from io import BytesIO

        from pypdf import PdfReader

        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t", landscape=True, margin_mm=15, author="virtUOS")
        doc.paragraph("quer")
        reader = PdfReader(BytesIO(doc.render()))
        box = reader.pages[0].mediabox
        self.assertGreater(float(box.width), float(box.height))
        self.assertEqual(reader.metadata.author, "virtUOS")
        self.assertAlmostEqual(doc.usable_width, float(box.width) - 2 * 15 * 72 / 25.4, places=3)

    def test_lazy_labels_resolve_at_use(self):
        from basicbar_pdf import PdfDocument
        page, image = LazyLabel("Seite %(page)s/%(pages)s"), LazyLabel("[Bild]")
        doc = PdfDocument("t", page_label=page, image_placeholder=image)
        page.text, image.text = "S. %(page)s von %(pages)s", "[Abbildung]"
        doc.rich('<p><img src="x"></p>')
        text = "\n".join(self._texts(doc.render()))
        self.assertIn("S. 1 von 1", text)
        self.assertIn("[Abbildung]", text)

    def test_auto_widths_fit_page_and_keep_words(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth

        from basicbar_pdf import FONT_BOLD, PdfDocument
        doc = PdfDocument("t", landscape=True)
        rows = [["Position", "Personalkosten gesamt", "2027"],
                ["Wissenschaftliche Hilfskraft", "12.345,00 €", "1"]]
        widths = doc.auto_widths(rows)
        self.assertAlmostEqual(sum(widths), doc.usable_width, places=3)
        self.assertGreaterEqual(widths[1], stringWidth("Personalkosten", FONT_BOLD, 9))
        self.assertGreaterEqual(widths[0], stringWidth("Wissenschaftliche Hilfskraft", FONT_BOLD, 9))
        wide = [[f"Spalte {i}" for i in range(40)], ["sehr-langer-wert-ohne-umbruch" * 2] * 40]
        self.assertAlmostEqual(sum(doc.auto_widths(wide)), doc.usable_width, places=3)
        self.assertEqual(doc.auto_widths([]), [])

    def test_number_table_alignment_and_strong_rows(self):
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.platypus import Table

        from basicbar_pdf import FONT, FONT_BOLD, PdfDocument
        doc = PdfDocument("t", landscape=True)
        doc.table([["Jahr", "2027", "Summe"], ["Kosten", "1.000 €", "1.000 €"],
                   ["Gesamt", "1.000 €", "1.000 €"]],
                  col_widths="auto", align_right_from=1, strong_rows=[2])
        table = next(f for f in doc._story if isinstance(f, Table))
        cells = table._cellvalues
        self.assertNotEqual(cells[1][0].style.alignment, TA_RIGHT)
        self.assertEqual(cells[1][1].style.alignment, TA_RIGHT)
        self.assertEqual(cells[0][2].style.alignment, TA_RIGHT)
        self.assertEqual(cells[2][0].style.fontName, FONT_BOLD)
        self.assertEqual(cells[1][0].style.fontName, FONT)
        self.assertIn("Gesamt", "\n".join(self._texts(doc.render())))

    def test_long_table_repeats_header_on_every_page(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t")
        doc.table([["Kopfzeile", "Wert"]] + [[f"Zeile {i}", str(i)] for i in range(150)],
                  col_widths="auto", align_right_from=1)
        pages = self._texts(doc.render())
        self.assertGreater(len(pages), 1)
        self.assertTrue(all("Kopfzeile" in page for page in pages))

    def test_add_raw_flowables(self):
        from reportlab.platypus import Paragraph

        from basicbar_pdf import PdfDocument, make_styles
        doc = PdfDocument("t")
        doc.add(Paragraph("roh", make_styles()["normal"]))
        self.assertIn("roh", "\n".join(self._texts(doc.render())))
