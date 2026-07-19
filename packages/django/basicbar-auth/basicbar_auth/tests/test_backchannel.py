# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""OIDC Back-Channel Logout (ported from ausleihbar)."""
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from basicbar_auth.oidc import BACKCHANNEL_LOGOUT_EVENT

User = get_user_model()


@override_settings(OIDC_RP_CLIENT_ID="test-client", OIDC_OP_ISSUER="")
class BackChannelLogoutTests(TestCase):
    def setUp(self):
        self.url = reverse("oidc-backchannel-logout")
        self.user = User.objects.create_user(username="demo", subject="sub-123")
        self.other = User.objects.create_user(username="other", subject="sub-999")

    def _login(self, user):
        """Create a real DB session for the user; return its key."""
        client = Client()
        client.force_login(user)
        return client.session.session_key

    def _valid_payload(self, sub="sub-123"):
        return {
            "iss": "https://idp.test/realms/x",
            "aud": "test-client",
            "sub": sub,
            "events": {BACKCHANNEL_LOGOUT_EVENT: {}},
        }

    @patch("basicbar_auth.oidc.OIDCBackend.verify_token")
    def test_valid_token_deletes_only_that_users_sessions(self, mock_verify):
        mine = self._login(self.user)
        theirs = self._login(self.other)
        mock_verify.return_value = self._valid_payload("sub-123")

        res = self.client.post(self.url, {"logout_token": "tok"})

        self.assertEqual(res.status_code, 200)
        self.assertFalse(Session.objects.filter(session_key=mine).exists())
        self.assertTrue(Session.objects.filter(session_key=theirs).exists())

    @patch("basicbar_auth.oidc.OIDCBackend.verify_token")
    def test_missing_event_is_rejected(self, mock_verify):
        key = self._login(self.user)
        payload = self._valid_payload()
        payload["events"] = {}
        mock_verify.return_value = payload

        res = self.client.post(self.url, {"logout_token": "tok"})

        self.assertEqual(res.status_code, 400)
        self.assertTrue(Session.objects.filter(session_key=key).exists())

    @patch("basicbar_auth.oidc.OIDCBackend.verify_token")
    def test_wrong_audience_is_rejected(self, mock_verify):
        payload = self._valid_payload()
        payload["aud"] = "someone-else"
        mock_verify.return_value = payload

        res = self.client.post(self.url, {"logout_token": "tok"})

        self.assertEqual(res.status_code, 400)

    @patch("basicbar_auth.oidc.OIDCBackend.verify_token")
    def test_issuer_mismatch_is_rejected(self, mock_verify):
        payload = self._valid_payload()
        mock_verify.return_value = payload
        with override_settings(OIDC_OP_ISSUER="https://expected.idp/realms/y"):
            res = self.client.post(self.url, {"logout_token": "tok"})
        self.assertEqual(res.status_code, 400)

    @patch(
        "basicbar_auth.oidc.OIDCBackend.verify_token",
        side_effect=Exception("bad sig"),
    )
    def test_invalid_signature_is_rejected(self, _mock_verify):
        res = self.client.post(self.url, {"logout_token": "tok"})
        self.assertEqual(res.status_code, 400)

    def test_missing_token_is_rejected(self):
        res = self.client.post(self.url, {})
        self.assertEqual(res.status_code, 400)

    def test_get_not_allowed(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 405)
