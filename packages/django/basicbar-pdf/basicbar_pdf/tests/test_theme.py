# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""PdfTheme: own font and colours, per-paragraph fallback to the bundled font, usable_height."""

import unittest
from io import BytesIO

from basicbar_pdf import theme as theme_module

ASCII = frozenset(range(32, 127))


def ascii_family():
    """A stand-in theme font: the bundled bold and bold italic files registered as "TestSans"
    (regular) and "TestSans-Bold", treated as ASCII-only (coverage patched). In a rendered PDF the
    theme font shows up as PlusJakartaSans-Bold, the fallback as PlusJakartaSans-Regular."""
    from basicbar_pdf import register_font_family
    from basicbar_pdf.fonts import FONT_DIR
    family = register_font_family("TestSans", regular=FONT_DIR / "PlusJakartaSans-Bold.ttf",
                                  bold=FONT_DIR / "PlusJakartaSans-BoldItalic.ttf")
    for name in family.names():
        theme_module._coverage[name] = ASCII
    return family


def fonts_in(data: bytes) -> set[str]:
    from pypdf import PdfReader
    names = set()
    for page in PdfReader(BytesIO(data)).pages:
        for font in page["/Resources"]["/Font"].values():
            names.add(str(font.get_object()["/BaseFont"]).split("+")[-1])
    return names


def texts(data: bytes) -> str:
    from pypdf import PdfReader
    return "\n".join(page.extract_text() for page in PdfReader(BytesIO(data)).pages)


class FontFamilyTests(unittest.TestCase):

    def test_missing_cuts_fall_back_to_the_nearest(self):
        family = ascii_family()
        self.assertEqual(family.bold, "TestSans-Bold")
        self.assertEqual(family.italic, "TestSans")
        self.assertEqual(family.bold_italic, "TestSans-Bold")

    def test_registering_again_is_harmless(self):
        self.assertEqual(ascii_family(), ascii_family())


class ThemeStyleTests(unittest.TestCase):

    def test_default_theme_keeps_the_frame_look(self):
        from reportlab.lib import colors

        from basicbar_pdf import FONT, FONT_BOLD, make_styles
        styles = make_styles()
        self.assertEqual(styles["normal"].fontName, FONT)
        self.assertEqual(styles["h1"].fontName, FONT_BOLD)
        self.assertEqual(styles["normal"].textColor.hexval(), colors.black.hexval())
        self.assertEqual(styles["muted"].textColor.hexval(), "0x666666")

    def test_theme_sets_font_and_colours(self):
        from basicbar_pdf import PdfDocument, PdfTheme
        family = ascii_family()
        theme = PdfTheme(fonts=family, text="#3e3e3f", heading="#ad1034", muted="#707070")
        doc = PdfDocument("t", theme=theme)
        self.assertEqual(doc.styles["normal"].fontName, "TestSans")
        self.assertEqual(doc.styles["cell_head"].fontName, "TestSans-Bold")
        self.assertEqual(doc.styles["normal"].textColor.hexval(), "0x3e3e3f")
        self.assertEqual(doc.styles["h2"].textColor.hexval(), "0xad1034")
        self.assertEqual(doc.styles["muted"].textColor.hexval(), "0x707070")

    def test_heading_colour_defaults_to_text(self):
        from basicbar_pdf import make_styles, PdfTheme
        styles = make_styles(PdfTheme(text="#123456"))
        self.assertEqual(styles["h3"].textColor.hexval(), "0x123456")


class ThemeFallbackTests(unittest.TestCase):

    def setUp(self):
        from basicbar_pdf import PdfTheme
        self.theme = PdfTheme(fonts=ascii_family())

    def test_safe_keeps_what_either_font_has(self):
        self.assertEqual(self.theme.safe("Grüße αβ 😀"), "Grüße ?? ?")

    def test_paragraph_switches_to_the_bundled_cut_of_the_same_weight(self):
        from basicbar_pdf import FONT, FONT_BOLD, PdfDocument
        doc = PdfDocument("t", theme=self.theme)
        doc.paragraph("Hallo")
        doc.paragraph("Grüße")
        doc.heading("Überschrift", 2)
        doc.paragraph("<b>&amp;</b> tags do not count", style="bold")
        fonts = [p.style.fontName for p in doc._story]
        self.assertEqual(fonts, ["TestSans", FONT, FONT_BOLD, "TestSans-Bold"])

    def test_rich_bullets_and_table_cells_fall_back_per_paragraph(self):
        from reportlab.platypus import Paragraph, Table

        from basicbar_pdf import FONT, PdfDocument
        doc = PdfDocument("t", theme=self.theme)
        doc.rich("<p>plain</p><p>Şahin</p><ul><li>ok</li><li>Łódź</li></ul>")
        doc.bullets(["eins", "zwei → drei"])
        doc.table([["Kopf"], ["Wert ü"]])
        paras = [f for f in doc._story if isinstance(f, Paragraph)]
        self.assertEqual([p.style.fontName for p in paras],
                         ["TestSans", FONT, "TestSans", FONT, "TestSans", FONT])
        table = next(f for f in doc._story if isinstance(f, Table))
        self.assertEqual(table._cellvalues[0][0].style.fontName, "TestSans-Bold")
        self.assertEqual(table._cellvalues[1][0].style.fontName, FONT)

    def test_render_embeds_theme_font_and_fallback_only_where_needed(self):
        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t", theme=self.theme, footer_left="Fusszeile")
        doc.paragraph("Nur ASCII")
        data = doc.render()
        self.assertIn("PlusJakartaSans-Bold", fonts_in(data))
        self.assertNotIn("PlusJakartaSans-Regular", fonts_in(data))  # the footer is in the theme font too

        doc = PdfDocument("t", theme=self.theme, footer_left="Fußzeile")
        doc.paragraph("Şahin → Łódź")
        data = doc.render()
        self.assertIn("PlusJakartaSans-Regular", fonts_in(data))
        self.assertIn("Şahin → Łódź", texts(data))
        self.assertIn("Fußzeile", texts(data))

    def test_auto_widths_measure_in_the_font_that_sets_the_cell(self):
        from reportlab.pdfbase.pdfmetrics import stringWidth

        from basicbar_pdf import FONT_BOLD, PdfDocument
        doc = PdfDocument("t", theme=self.theme)
        widths = doc.auto_widths([["Größe", "x"]])
        self.assertGreaterEqual(widths[0], stringWidth("Größe", FONT_BOLD, 9))


class UsableHeightTests(unittest.TestCase):

    def test_usable_height_is_the_frame_less_its_padding(self):
        from reportlab.lib.pagesizes import A4

        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t")
        self.assertAlmostEqual(doc.usable_height, A4[1] - doc.margin - doc.bottom - 12, places=3)

    def test_box_just_taller_than_the_frame_still_renders(self):
        from reportlab.platypus import Spacer

        from basicbar_pdf import PdfDocument
        doc = PdfDocument("t")
        # the box table adds 10 pt of padding: inner + 10 lands 0.3 pt above the usable height,
        # where the old check (measured without that padding) still framed it and the render failed
        doc.box(lambda d: d.add(Spacer(1, doc.usable_height - 9.7)))
        self.assertTrue(doc.render().startswith(b"%PDF"))
