# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)
from django.test import SimpleTestCase

from basicbar_integrations.html_sanitize import clean_html, clean_media_url


class HtmlSanitizeTests(SimpleTestCase):
    def test_keeps_supported_formatting(self):
        html = "<p>Hi <strong>bold</strong> <em>it</em></p><ul><li>a</li></ul>"
        self.assertEqual(clean_html(html), html)

    def test_allows_headings_h2_h3_but_drops_h1(self):
        self.assertEqual(clean_html("<h1>a</h1><h2>b</h2><h3>c</h3>"), "a<h2>b</h2><h3>c</h3>")

    def test_keeps_external_link_and_forces_rel_noopener(self):
        self.assertEqual(
            clean_html('<a href="https://example.org">x</a>'),
            '<a href="https://example.org" rel="noopener">x</a>',
        )

    def test_strips_javascript_href(self):
        self.assertNotIn("javascript", clean_html('<a href="javascript:alert(1)">x</a>'))

    def test_keeps_media_image(self):
        self.assertEqual(
            clean_html('<img src="/media/a.png" alt="x">'), '<img src="/media/a.png" alt="x">'
        )

    def test_drops_external_image_src(self):
        self.assertNotIn("evil", clean_html('<img src="https://evil/x.png">'))

    def test_removes_scripts_and_event_handlers(self):
        self.assertEqual(clean_html('<p onclick="x">hi<script>bad()</script></p>'), "<p>hi</p>")

    def test_empty_input_returns_empty_string(self):
        self.assertEqual(clean_html(""), "")
        self.assertEqual(clean_html(None), "")

    def test_clean_media_url_accepts_only_local_media(self):
        self.assertEqual(clean_media_url("/media/x.png"), "/media/x.png")
        self.assertEqual(clean_media_url("https://evil/x.png"), "")
        self.assertEqual(clean_media_url("/media/../etc/passwd"), "")
        self.assertEqual(clean_media_url("//evil/x.png"), "")
