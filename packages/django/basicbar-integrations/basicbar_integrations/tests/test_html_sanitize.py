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

    def test_clean_media_url_rejects_encoded_path_traversal(self):
        for url in (
            "/media/%2e%2e/api/whoami/",
            "/media/.%2E/x",
            "/media/%2E%2E/x",
            "/media/%252e%252e/x",
            "/media/..%2fapi",
            "/media/a\\..\\b",
            "/media/a/../../api",
            "//evil.example/media/x",
            "https://evil.example/media/x",
        ):
            self.assertEqual(clean_media_url(url), "", url)

    def test_clean_media_url_keeps_valid_paths(self):
        self.assertEqual(clean_media_url("/media/rich/abc.png"), "/media/rich/abc.png")
        self.assertEqual(
            clean_media_url("/media/products/Kuche2.jpeg"), "/media/products/Kuche2.jpeg"
        )
        self.assertEqual(clean_media_url("/media/rich/a%20b.png"), "/media/rich/a%20b.png")
        self.assertEqual(clean_media_url("/media/rich/gr%C3%BC%C3%9F.png"), "/media/rich/gr%C3%BC%C3%9F.png")

    def test_clean_html_drops_img_src_with_encoded_traversal(self):
        self.assertNotIn("api", clean_html('<img src="/media/%2e%2e/api/">'))

    def test_clean_media_url_rejects_control_characters(self):
        for url in (
            "/media/.\t./api/",
            "/media/.\n./api/",
            "/media/%2e\r%2e/api/",
            "/media/%09",
        ):
            self.assertEqual(clean_media_url(url), "", repr(url))

    def test_clean_media_url_rejects_query_or_fragment(self):
        for url in (
            "/media/..?x",
            "/media/.%2e?x",
            "/media/%2e%2e#f",
            "/media/rich/a.png?v=1",
        ):
            self.assertEqual(clean_media_url(url), "", url)

    def test_clean_media_url_rejects_over_length_url_instead_of_truncating(self):
        # Validated-then-truncated would cut this back down to ".../../..zzz"
        # which normalises outside /media/ — must be rejected outright.
        url = "/media/" + "a" * 287 + "/../..zzz"
        self.assertEqual(len(url), 303)
        self.assertEqual(clean_media_url(url), "")

    def test_clean_html_drops_img_src_with_encoded_control_char(self):
        self.assertNotIn("api", clean_html('<img src="/media/.&#9;./api/whoami/">'))
