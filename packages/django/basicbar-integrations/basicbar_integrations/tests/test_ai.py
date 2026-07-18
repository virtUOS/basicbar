# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)
import json
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings

from basicbar_integrations import ai


class AiIsEnabledTests(SimpleTestCase):
    def test_disabled_by_default(self):
        # No settings configured at all — the package defaults apply.
        self.assertFalse(ai.is_enabled())

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="k", AI_MODEL="qwen-3.5",
    )
    def test_enabled_when_fully_configured(self):
        self.assertTrue(ai.is_enabled())

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="", AI_MODEL="qwen-3.5",
    )
    def test_disabled_without_key(self):
        self.assertFalse(ai.is_enabled())


class AiChatJsonTests(SimpleTestCase):
    @override_settings(AI_PROVIDER="none")
    def test_raises_when_disabled(self):
        with self.assertRaises(ai.AIError):
            ai.chat_json("s", "u")

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="k", AI_MODEL="qwen-3.5", AI_TIMEOUT=5,
    )
    def test_parses_model_json_reply(self):
        reply = {"choices": [{"message": {"content": json.dumps({"attributes": [1, 2]})}}]}
        fake = MagicMock()
        fake.read.return_value = json.dumps(reply).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value = fake
        with patch("basicbar_integrations.ai.request.urlopen", return_value=cm):
            out = ai.chat_json("s", "u")
        self.assertEqual(out, {"attributes": [1, 2]})

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="k", AI_MODEL="qwen-3.5", AI_TIMEOUT=5,
    )
    def test_bad_json_raises_aierror(self):
        fake = MagicMock()
        fake.read.return_value = b"not json"
        cm = MagicMock()
        cm.__enter__.return_value = fake
        with patch("basicbar_integrations.ai.request.urlopen", return_value=cm):
            with self.assertRaises(ai.AIError):
                ai.chat_json("s", "u")

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="k", AI_MODEL="qwen-3.5", AI_TIMEOUT=5,
    )
    def test_null_content_raises_aierror(self):
        reply = {"choices": [{"message": {"content": None}}]}
        fake = MagicMock()
        fake.read.return_value = json.dumps(reply).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value = fake
        with patch("basicbar_integrations.ai.request.urlopen", return_value=cm):
            with self.assertRaises(ai.AIError):
                ai.chat_json("s", "u")

    def _sent_payload(self):
        """Run chat_json against a stub reply and return the JSON body it POSTed."""
        reply = {"choices": [{"message": {"content": "{}"}}]}
        fake = MagicMock()
        fake.read.return_value = json.dumps(reply).encode("utf-8")
        cm = MagicMock()
        cm.__enter__.return_value = fake
        with patch("basicbar_integrations.ai.request.urlopen", return_value=cm) as urlopen:
            ai.chat_json("s", "u")
        sent_request = urlopen.call_args.args[0]
        return json.loads(sent_request.data.decode("utf-8"))

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="k", AI_MODEL="qwen-3.5", AI_TIMEOUT=5,
        AI_MAX_TOKENS=2000, AI_DISABLE_THINKING=True,
    )
    def test_disables_thinking_and_uses_configured_max_tokens(self):
        body = self._sent_payload()
        self.assertEqual(body["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(body["max_tokens"], 2000)

    @override_settings(
        AI_PROVIDER="litellm", AI_BASE_URL="https://x/v1",
        AI_API_KEY="k", AI_MODEL="qwen-3.5", AI_TIMEOUT=5,
        AI_MAX_TOKENS=2000, AI_DISABLE_THINKING=False,
    )
    def test_no_thinking_flag_when_disabled_off(self):
        body = self._sent_payload()
        self.assertNotIn("chat_template_kwargs", body)
