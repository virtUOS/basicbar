# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)
import json
from unittest.mock import MagicMock, patch
from urllib import error

from django.test import SimpleTestCase, override_settings

from basicbar_integrations import translation_service

LT_ON = {
    "CONTENT_TRANSLATION_PROVIDER": "libretranslate",
    "LIBRETRANSLATE_URL": "http://libretranslate.local",
}
LT_OFF = {"CONTENT_TRANSLATION_PROVIDER": "none", "LIBRETRANSLATE_URL": ""}


def _mock_response(body: str):
    fake = MagicMock()
    fake.read.return_value = body.encode("utf-8")
    cm = MagicMock()
    cm.__enter__.return_value = fake
    return cm


class TranslationServiceTests(SimpleTestCase):
    def test_disabled_by_default(self):
        # No settings configured at all — the package defaults apply.
        self.assertFalse(translation_service.is_enabled())

    @override_settings(**LT_ON)
    def test_enabled_when_configured(self):
        self.assertTrue(translation_service.is_enabled())

    @override_settings(**{**LT_ON, "LIBRETRANSLATE_URL": ""})
    def test_disabled_without_url(self):
        self.assertFalse(translation_service.is_enabled())

    @override_settings(**LT_OFF)
    def test_translate_raises_when_disabled(self):
        with self.assertRaises(translation_service.TranslationError):
            translation_service.translate("Hallo", "de", "en")

    def test_translate_returns_unchanged_for_blank_text(self):
        # No provider needed — short-circuits before any network call.
        self.assertEqual(translation_service.translate("", "de", "en"), "")
        self.assertEqual(translation_service.translate("   ", "de", "en"), "   ")

    def test_translate_returns_unchanged_when_languages_match(self):
        self.assertEqual(translation_service.translate("Hallo", "de", "de"), "Hallo")

    @override_settings(**LT_ON)
    def test_translate_calls_libretranslate(self):
        body = '{"translatedText": "Hello"}'
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            return_value=_mock_response(body),
        ) as urlopen:
            self.assertEqual(translation_service.translate("Hallo", "de", "en"), "Hello")
        sent = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(sent["format"], "text")
        self.assertNotIn("api_key", sent)

    @override_settings(**{**LT_ON, "LIBRETRANSLATE_API_KEY": "sekrit"})
    def test_translate_sends_api_key_when_configured(self):
        body = '{"translatedText": "Hello"}'
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            return_value=_mock_response(body),
        ) as urlopen:
            translation_service.translate("Hallo", "de", "en")
        sent = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(sent["api_key"], "sekrit")

    @override_settings(**LT_ON)
    def test_translate_html_sends_html_format(self):
        body = '{"translatedText": "<p>Hello</p>"}'
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            return_value=_mock_response(body),
        ) as urlopen:
            result = translation_service.translate("<p>Hallo</p>", "de", "en", html=True)
        self.assertEqual(result, "<p>Hello</p>")
        sent = json.loads(urlopen.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(sent["format"], "html")

    @override_settings(**LT_ON)
    def test_upstream_error_raises_translation_error(self):
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            side_effect=error.URLError("boom"),
        ):
            with self.assertRaises(translation_service.TranslationError):
                translation_service.translate("Hallo", "de", "en")

    @override_settings(**LT_ON)
    def test_empty_reply_raises_translation_error(self):
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            return_value=_mock_response("{}"),
        ):
            with self.assertRaises(translation_service.TranslationError):
                translation_service.translate("Hallo", "de", "en")
