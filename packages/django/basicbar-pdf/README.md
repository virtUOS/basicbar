# basicbar-pdf

Gemeinsamer PDF-Rahmen der „-bar“-Tools für herunterladbare Dokumente
(Protokolle, Berichte): [reportlab](https://www.reportlab.com/) mit der
mitgelieferten Schrift **Plus Jakarta Sans** (SIL OFL 1.1, `basicbar_pdf/fonts/OFL.txt`),
A4 hoch oder quer, Fußzeile „Seite x von y“ auf jeder Seite. Ein Tool kann
eigene Schrift und Farben setzen (Theme, siehe unten).

Kein Django nötig: die einzigen sichtbaren Texte des Rahmens (Seitenangabe,
Bild-Platzhalter) sind Parameter; das Tool übergibt seine Übersetzungen
(`gettext_lazy` funktioniert, sie werden erst beim Rendern aufgelöst).

## Einbinden

```text
# requirements.txt
basicbar-pdf @ https://github.com/virtUOS/basicbar/archive/refs/tags/pdf/v0.2.0.tar.gz#subdirectory=packages/django/basicbar-pdf
```

```python
from django.utils.translation import gettext as _, gettext_lazy
from basicbar_pdf import PdfDocument

doc = PdfDocument(
    _("Protocol"),
    footer_left="Fachbereichsrat – 12. Sitzung",
    page_label=gettext_lazy("Page %(page)s of %(pages)s"),
    image_placeholder=gettext_lazy("[Image]"),
)
doc.heading(_("Attendance"), 2)
doc.paragraph("…", style="muted")       # normal | small | bold | muted
doc.rich(question_html)                  # Editor-HTML (TipTap-Teilmenge)
doc.table(rows, col_widths="auto", align_right_from=1, strong_rows=[len(rows) - 1])
doc.box(lambda d: d.paragraph("Siegel …"))
pdf_bytes = doc.render()
```

Die msgids `"Page %(page)s of %(pages)s"` und `"[Image]"` gehören in den
Übersetzungskatalog des Tools (Deutsch: „Seite %(page)s von %(pages)s“, „[Bild]“).

## API

`PdfDocument(title, *, footer_left="", author="", landscape=False, margin_mm=20,
page_label="Page %(page)s of %(pages)s", image_placeholder="[Image]", compress=True, theme=None)`

| Methode | Zweck |
|---|---|
| `heading(text, level=1)` | Überschrift h1–h3 |
| `paragraph(text, *, style="normal")` | Absatz (Text wird escaped, `\n` = Zeilenumbruch) |
| `rich(html)` | Editor-HTML: Absätze, fett/kursiv/unterstrichen/durchgestrichen, Listen, h1–h3, Zitate, Links (URL in Klammern), Tabellen/`pre` vereinfacht, Bilder als Platzhalter; unbekannte Tags fallen weg, ihr Text bleibt |
| `bullets(items)` | Aufzählung |
| `table(rows, *, header=True, col_widths=None, align_right_from=None, strong_rows=())` | Gitter-Tabelle, Kopfzeile wiederholt sich auf jeder Seite; `col_widths="auto"` misst die Spalten (kein Wort wird getrennt), `align_right_from` setzt Zahlenspalten rechtsbündig, `strong_rows` fettet Zeilen (Kopfzeile = 0) |
| `auto_widths(rows, *, header=True)` | die Spaltenbreiten von `col_widths="auto"` |
| `usable_width` | Breite zwischen den Rändern in Punkt |
| `usable_height` | Höhe, die ein Flowable auf einer Seite haben darf (Satzspiegel abzüglich Innenabstand des Rahmens), in Punkt; für eigene Bausteine über `add()` |
| `rule()`, `spacer(mm=3)` | Trennlinie, Abstand |
| `keep_together(builder)` | Block bleibt auf einer Seite, wenn er passt |
| `box(builder)` | hellgrau gerahmter Block; höher als eine Seite → ungerahmt |
| `add(*flowables)` | eigene reportlab-Flowables |
| `render() -> bytes` | das PDF |

Außerdem: `safe_text(text)` (Zeichen, die die Schrift nicht hat — Griechisch,
Kyrillisch, CJK, Emoji — werden zu „?“), `html_to_flowables(html, styles, theme=None)`,
`make_styles(theme=None)`, `FONT`, `FONT_BOLD`.

## Theme: eigene Schrift und Farben

```python
from pathlib import Path
from basicbar_pdf import PdfDocument, PdfTheme, register_font_family

FONTS = Path(__file__).parent / "fonts"
signika = register_font_family(
    "Signika", regular=FONTS / "Signika-Regular.ttf", bold=FONTS / "Signika-Bold.ttf",
)  # ohne Kursive: kursiv fällt auf normal, fett-kursiv auf fett
THEME = PdfTheme(fonts=signika, text="#3e3e3f", heading="#ad1034", box_fill="#f3f3f3")

doc = PdfDocument(_("Recommendations"), theme=THEME)
```

`PdfTheme` (unveränderlich; die Standardwerte sind das bisherige Aussehen):

| Feld | Standard | Wirkung |
|---|---|---|
| `fonts` | Plus Jakarta Sans | Schriftfamilie (`FontFamily`, von `register_font_family`) |
| `text` | `#000000` | Fließtext |
| `muted` | `#666666` | Stil `muted` |
| `heading` | wie `text` | h1–h3 |
| `quote` | `#444444` | Zitate |
| `grid`, `table_head` | `#c8c8c8`, `#eeeeee` | Tabellenlinien und `rule()`, Tabellenkopf |
| `box_fill`, `box_border` | `#f3f3f3`, `#aaaaaa` | `box()` |
| `footer` | `#555555` | Fußzeile (in der Theme-Schrift) |

**Ersatzschrift je Absatz:** Hat ein Absatz Zeichen, die der Theme-Schrift
fehlen, die mitgelieferte Plus Jakarta Sans aber hat, wird er in der
mitgelieferten Schrift gesetzt (gleicher Schnitt). Nur was keine der beiden
Schriften hat, wird zu „?“. Eigene Flowables über `add()` können dasselbe mit
`theme.paragraph(markup, style)` und `theme.safe(text)` tun.

## Tests

```bash
pip install "./packages/django/basicbar-pdf[test]"
cd packages/django/basicbar-pdf && python runtests.py
```
