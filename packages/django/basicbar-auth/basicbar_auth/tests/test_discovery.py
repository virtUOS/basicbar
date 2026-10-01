# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

import io
import json
from unittest.mock import patch

from django.test import SimpleTestCase

from basicbar_auth.discovery import discover_endpoints


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class DiscoveryTests(SimpleTestCase):
    @patch("basicbar_auth.discovery.urllib.request.urlopen")
    def test_returns_the_document(self, mock_open):
        doc = {"authorization_endpoint": "https://idp.test/auth", "jwks_uri": "https://idp.test/jwks"}
        mock_open.return_value = _Response(json.dumps(doc).encode())
        self.assertEqual(discover_endpoints("https://idp.test/realms/x/"), doc)
        url = mock_open.call_args.args[0]
        self.assertEqual(url, "https://idp.test/realms/x/.well-known/openid-configuration")

    @patch("basicbar_auth.discovery.urllib.request.urlopen", side_effect=OSError("unreachable"))
    def test_failure_is_logged_and_returns_empty(self, _mock_open):
        with self.assertLogs("basicbar_auth.discovery", level="WARNING") as logs:
            self.assertEqual(discover_endpoints("https://idp.test"), {})
        self.assertIn("unreachable", logs.output[0])

    @patch("basicbar_auth.discovery.urllib.request.urlopen")
    def test_non_object_document_is_rejected(self, mock_open):
        mock_open.return_value = _Response(b"[1, 2]")
        with self.assertLogs("basicbar_auth.discovery", level="WARNING"):
            self.assertEqual(discover_endpoints("https://idp.test"), {})
