# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)
from unittest.mock import MagicMock, patch
from urllib import error

from django.contrib.auth.models import User
from django.test import TestCase, override_settings

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


class TranslateEndpointTests(TestCase):
    """POST /api/translate/ — the canonical translate contract."""

    def setUp(self):
        self.user = User.objects.create_user(username="frank")

    def _post(self, **overrides):
        payload = {"text": "Hallo", "source": "de", "target": "en"}
        payload.update(overrides)
        return self.client.post(
            "/api/translate/", payload, content_type="application/json"
        )

    def test_unauthenticated_forbidden(self):
        self.assertEqual(self._post().status_code, 403)

    @override_settings(**LT_OFF)
    def test_disabled_returns_503(self):
        self.client.force_login(self.user)
        self.assertEqual(self._post().status_code, 503)

    @override_settings(**LT_ON)
    def test_unknown_language_returns_400(self):
        self.client.force_login(self.user)
        self.assertEqual(self._post(target="xx").status_code, 400)

    @override_settings(**LT_ON)
    def test_success_returns_translated_text(self):
        self.client.force_login(self.user)
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            return_value=_mock_response('{"translatedText": "Hello"}'),
        ):
            response = self._post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"translated": "Hello"})

    @override_settings(**LT_ON)
    def test_upstream_error_returns_502_not_stacktrace(self):
        self.client.force_login(self.user)
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            side_effect=error.URLError("boom"),
        ):
            response = self._post()
        self.assertEqual(response.status_code, 502)
        self.assertIn("detail", response.json())

    @override_settings(**LT_ON)
    def test_html_result_is_sanitized(self):
        self.client.force_login(self.user)
        body = '{"translatedText": "<p>Hi</p><script>alert(1)</script>"}'
        with patch(
            "basicbar_integrations.translation_service.request.urlopen",
            return_value=_mock_response(body),
        ):
            response = self._post(text="<p>Hallo</p>", format="html")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"translated": "<p>Hi</p>"})


class CapabilitiesEndpointTests(TestCase):
    """GET /api/capabilities/ — feature discovery for the frontend."""

    def test_everything_off_by_default(self):
        response = self.client.get("/api/capabilities/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"translation": False, "ai": False})

    @override_settings(**LT_ON)
    def test_reports_enabled_translation(self):
        response = self.client.get("/api/capabilities/")
        self.assertEqual(response.json(), {"translation": True, "ai": False})

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="k", AI_MODEL="qwen-3.5",
    )
    def test_reports_enabled_ai(self):
        response = self.client.get("/api/capabilities/")
        self.assertEqual(response.json(), {"translation": False, "ai": True})
