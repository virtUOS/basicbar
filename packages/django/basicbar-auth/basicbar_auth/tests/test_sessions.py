# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""The user → session index and its use by the back-channel logout."""
import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from basicbar_auth.models import UserSession
from basicbar_auth.oidc import BACKCHANNEL_LOGOUT_EVENT, _delete_sessions_for_subject

User = get_user_model()


class SessionIndexTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", subject="sub-123")

    def test_login_records_the_session(self):
        client = Client()
        client.force_login(self.user)
        key = client.session.session_key
        self.assertTrue(UserSession.objects.filter(user=self.user, session_key=key).exists())

    def test_logout_forgets_the_session(self):
        client = Client()
        client.force_login(self.user)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        client.logout()
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 0)

    def test_two_browsers_two_rows(self):
        a, b = Client(), Client()
        a.force_login(self.user)
        b.force_login(self.user)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 2)

    def test_delete_by_subject_uses_the_index(self):
        a, b = Client(), Client()
        a.force_login(self.user)
        b.force_login(self.user)
        keys = {a.session.session_key, b.session.session_key}

        with patch("basicbar_auth.oidc.Session.objects.filter", wraps=Session.objects.filter) as spy:
            deleted = _delete_sessions_for_subject("sub-123")

        self.assertEqual(deleted, 2)
        self.assertFalse(Session.objects.filter(session_key__in=keys).exists())
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 0)
        # One indexed lookup by key — no scan over the unexpired session table.
        self.assertEqual(spy.call_count, 1)
        self.assertEqual(set(spy.call_args.kwargs["session_key__in"]), keys)

    def test_falls_back_to_a_scan_for_unindexed_sessions(self):
        # A session from before the index existed: logged in, index row gone.
        client = Client()
        client.force_login(self.user)
        key = client.session.session_key
        UserSession.objects.all().delete()

        deleted = _delete_sessions_for_subject("sub-123")

        self.assertEqual(deleted, 1)
        self.assertFalse(Session.objects.filter(session_key=key).exists())

    def test_unknown_subject_deletes_nothing(self):
        Client().force_login(self.user)
        self.assertEqual(_delete_sessions_for_subject("nobody"), 0)
        self.assertEqual(Session.objects.count(), 1)


@override_settings(OIDC_RP_CLIENT_ID="test-client", OIDC_OP_ISSUER="")
class BackChannelUsesIndexTests(TestCase):
    @patch("basicbar_auth.oidc.OIDCBackend.verify_token")
    def test_backchannel_logout_drops_indexed_sessions_only_for_that_user(self, mock_verify):
        me = User.objects.create_user(username="me", subject="sub-me")
        other = User.objects.create_user(username="other", subject="sub-other")
        mine, theirs = Client(), Client()
        mine.force_login(me)
        theirs.force_login(other)
        mock_verify.return_value = {
            "iss": "https://idp.test/realms/x",
            "aud": "test-client",
            "sub": "sub-me",
            "iat": int(time.time()),
            "events": {BACKCHANNEL_LOGOUT_EVENT: {}},
        }

        res = self.client.post(reverse("oidc-backchannel-logout"), {"logout_token": "tok"})

        self.assertEqual(res.status_code, 200)
        self.assertFalse(mine.get("/api/whoami/").json()["authenticated"])
        self.assertTrue(theirs.get("/api/whoami/").json()["authenticated"])
        self.assertEqual(UserSession.objects.filter(user=me).count(), 0)
        self.assertEqual(UserSession.objects.filter(user=other).count(), 1)
