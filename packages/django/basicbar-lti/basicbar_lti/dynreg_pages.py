# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Minimal bilingual HTML pages for the Dynamic Registration view.

Every dynamic value goes through format_html/escape; the inline
scripts contain no dynamic values.
"""
from django.utils.html import format_html
from django.utils.safestring import mark_safe

# Tells the platform to close the registration iframe/window (IMS LTI DR).
_CLOSE_MESSAGE = (
    '(window.opener || window.parent).postMessage('
    '{subject: "org.imsglobal.lti.close"}, "*");'
)

CLOSE_SCRIPT = mark_safe(f"<script>{_CLOSE_MESSAGE}</script>")  # noqa: S308

# Wires the "Abbrechen" button (id=cancel) to the close message.
CANCEL_SCRIPT = mark_safe(  # noqa: S308
    '<script>document.getElementById("cancel").addEventListener("click", '
    f"function () {{ {_CLOSE_MESSAGE} }});</script>"
)


def page(title_de, title_en, body_html, *, close=False):
    """A complete HTML document; body_html must already be safe HTML."""
    return format_html(
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>{} / {}</title>"
        "<style>body{{font-family:system-ui,sans-serif;max-width:40rem;"
        "margin:2rem auto;padding:0 1rem;line-height:1.5}}"
        "p.en{{color:#555}}button{{font:inherit;margin-right:.5rem}}</style>"
        "</head><body><h1>{}</h1><h2 lang=\"en\">{}</h2>{}{}</body></html>",
        title_de,
        title_en,
        title_de,
        title_en,
        body_html,
        CLOSE_SCRIPT if close else "",
    )
