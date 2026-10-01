# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Session endpoints and the tolerant OIDC callback (ported from the tools)."""
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

User = get_user_model()


class WhoamiTests(TestCase):
    def test_anonymous(self):
        payload = self.client.get("/api/whoami/").json()
        self.assertFalse(payload["authenticated"])
        # An authoritative CSRF token is always returned so the SPA can send
        # unsafe requests reliably (esp. cross-origin in dev).
        self.assertTrue(payload["csrf_token"])
        self.assertNotIn("username", payload)

    def test_authenticated(self):
        user = User.objects.create_user(
            username="frank", subject="abc-123", first_name="Frank", language="de"
        )
        self.client.force_login(user)
        payload = self.client.get("/api/whoami/").json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual(payload["username"], "frank")
        self.assertEqual(payload["first_name"], "Frank")
        self.assertEqual(payload["subject"], "abc-123")
        self.assertEqual(payload["language"], "de")
        self.assertFalse(payload["is_staff"])
        self.assertTrue(payload["csrf_token"])


class SetLanguageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="frank")

    def _post(self, body):
        return self.client.post(
            "/api/whoami/language/", body, content_type="application/json"
        )

    def test_sets_supported_language(self):
        self.client.force_login(self.user)
        response = self._post({"language": "de"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"language": "de"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, "de")

    def test_rejects_unknown_language(self):
        self.client.force_login(self.user)
        self.assertEqual(self._post({"language": "xx"}).status_code, 400)
        self.assertEqual(self._post({"language": ""}).status_code, 400)
        self.assertEqual(self._post([1, 2]).status_code, 400)

    def test_tolerates_broken_json(self):
        self.client.force_login(self.user)
        response = self.client.post(
            "/api/whoami/language/", "{not json", content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)

    def test_requires_authentication(self):
        self.assertEqual(self._post({"language": "de"}).status_code, 403)

    def test_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/whoami/language/").status_code, 405)


class LogoutViewTests(TestCase):
    def test_anonymous_goes_straight_to_the_spa(self):
        response = self.client.get("/oidc/logout-redirect/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://spa.test/")

    def test_authenticated_is_sent_to_the_provider_end_session(self):
        user = User.objects.create_user(username="frank")
        self.client.force_login(user)
        session = self.client.session
        session["oidc_id_token"] = "id-token"
        session.save()

        response = self.client.get("/oidc/logout-redirect/")

        self.assertEqual(response.status_code, 302)
        location = response["Location"]
        self.assertTrue(location.startswith("https://idp.test/logout?"))
        self.assertIn("id_token_hint=id-token", location)
        self.assertIn("client_id=test-client", location)
        self.assertIn("post_logout_redirect_uri=http%3A%2F%2Fspa.test%2F", location)
        # The Django session is gone either way.
        self.assertFalse(self.client.get("/api/whoami/").json()["authenticated"])

    @override_settings(OIDC_OP_LOGOUT_ENDPOINT="")
    def test_without_end_session_endpoint_logs_out_locally(self):
        user = User.objects.create_user(username="frank")
        self.client.force_login(user)
        response = self.client.get("/oidc/logout-redirect/")
        self.assertEqual(response["Location"], "http://spa.test/")
        self.assertFalse(self.client.get("/api/whoami/").json()["authenticated"])


class SafeOIDCCallbackViewTests(TestCase):
    def test_stale_callback_redirects_instead_of_400(self):
        # A replayed callback (Back after login): the session still has its
        # ``oidc_states`` dict, but this state was consumed by the first
        # callback — mozilla raises SuspiciousOperation for exactly that.
        session = self.client.session
        session["oidc_states"] = {"other": {"nonce": "n"}}
        session.save()

        response = self.client.get("/oidc/callback/?code=abc&state=spent")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://spa.test/")
        self.assertFalse(self.client.get("/api/whoami/").json()["authenticated"])

    def test_callback_without_any_pending_login_goes_to_login_failure(self):
        # No ``oidc_states`` at all (fresh browser): mozilla's own graceful path.
        response = self.client.get("/oidc/callback/?code=abc&state=spent")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")

    def test_provider_error_still_goes_to_login_failure(self):
        response = self.client.get("/oidc/callback/?error=login_required")
        self.assertEqual(response.status_code, 302)
        # mozilla's own failure redirect (LOGIN_REDIRECT_URL_FAILURE, default "/").
        self.assertEqual(response["Location"], "/")
