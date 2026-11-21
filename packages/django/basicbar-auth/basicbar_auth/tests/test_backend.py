# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Claim mapping, account cap, subject handling and token verification."""
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from basicbar_auth.oidc import OIDCBackend
from basicbar_auth.tests.tokens import jwks, make_token, public_key_pem, requires_pyjwt

User = get_user_model()

CLAIMS = {
    "sub": "abc-123",
    "preferred_username": "frank",
    "email": "frank@uni-osnabrueck.de",
    "given_name": "Frank",
    "family_name": "Lehrender",
    "groups": [],
}


class OIDCClaimMappingTests(TestCase):
    def setUp(self):
        self.backend = OIDCBackend()

    def test_create_user_from_claims(self):
        user = self.backend.create_user(CLAIMS)
        self.assertEqual(user.subject, "abc-123")
        self.assertEqual(user.username, "frank")
        self.assertEqual(user.email, "frank@uni-osnabrueck.de")
        self.assertEqual(user.first_name, "Frank")
        self.assertEqual(user.claims["email"], "frank@uni-osnabrueck.de")
        self.assertFalse(user.is_staff)

    def test_filter_users_by_subject(self):
        self.backend.create_user(CLAIMS)
        self.assertEqual(self.backend.filter_users_by_claims({"sub": "abc-123"}).count(), 1)
        self.assertEqual(self.backend.filter_users_by_claims({"sub": "nope"}).count(), 0)
        self.assertEqual(self.backend.filter_users_by_claims({}).count(), 0)

    def test_update_user_backfills_subject(self):
        user = User.objects.create(username="x", subject=None)
        self.backend.update_user(user, {"sub": "new-sub", "email": "x@y.org"})
        user.refresh_from_db()
        self.assertEqual(user.subject, "new-sub")
        self.assertEqual(user.email, "x@y.org")

    def test_update_user_refreshes_claims(self):
        user = self.backend.create_user(CLAIMS)
        updated = self.backend.update_user(user, {**CLAIMS, "email": "neu@uni-osnabrueck.de"})
        self.assertEqual(updated.email, "neu@uni-osnabrueck.de")

    @override_settings(OIDC_CLAIM_USERNAME="nickname")
    def test_username_claim_is_configurable(self):
        user = self.backend.create_user({"sub": "s1", "nickname": "robin"})
        self.assertEqual(user.username, "robin")

    def test_login_records_last_login(self):
        # Retention jobs key on last_login, so OIDC auth must set it.
        user = self.backend.create_user({"sub": "s2", "preferred_username": "a"})
        self.assertIsNotNone(user.last_login)
        user.last_login = None
        user.save(update_fields=["last_login"])
        self.backend.update_user(user, {"sub": "s2"})
        user.refresh_from_db()
        self.assertIsNotNone(user.last_login)


class MaxUsersCapTests(TestCase):
    def setUp(self):
        self.backend = OIDCBackend()

    @override_settings(MAX_USERS=1)
    def test_user_cap_refuses_new_identity(self):
        self.backend.create_user({"sub": "first", "preferred_username": "one"})
        with self.assertRaises(PermissionDenied):
            self.backend.create_user({"sub": "second", "preferred_username": "two"})

    @override_settings(MAX_USERS=1)
    def test_user_cap_ignores_anonymized_accounts(self):
        user = self.backend.create_user({"sub": "first", "preferred_username": "one"})
        user.anonymized_at = timezone.now()
        user.save(update_fields=["anonymized_at"])
        # The anonymized account frees its slot, so a new identity fits.
        self.backend.create_user({"sub": "second", "preferred_username": "two"})
        self.assertEqual(User.objects.count(), 2)

    def test_no_cap_by_default(self):
        for i in range(3):
            self.backend.create_user({"sub": f"s{i}", "preferred_username": f"u{i}"})
        self.assertEqual(User.objects.count(), 3)


class SubjectDriftTests(TestCase):
    """The username fallback is an explicit opt-in — see the operator notes."""

    def setUp(self):
        self.backend = OIDCBackend()
        self.user = self.backend.create_user(CLAIMS)
        self.drifted = {**CLAIMS, "sub": "new-sub-456"}

    def test_disabled_by_default_a_drifted_subject_matches_nothing(self):
        self.assertEqual(self.backend.filter_users_by_claims(self.drifted).count(), 0)

    @override_settings(OIDC_MATCH_BY_USERNAME_FALLBACK=True)
    def test_opt_in_falls_back_to_username_and_adopts_subject(self):
        """A re-imported dev realm (or an IdP migration) re-issues subjects;
        the login must match the existing account instead of crashing into
        the unique-username constraint."""
        with self.assertLogs("basicbar_auth.oidc", level="WARNING"):
            matched = self.backend.filter_users_by_claims(self.drifted)
        self.assertEqual(list(matched), [self.user])
        # update_user adopts the new subject, so the next login matches
        # directly again.
        updated = self.backend.update_user(self.user, self.drifted)
        self.assertEqual(updated.subject, "new-sub-456")
        self.assertEqual(self.backend.filter_users_by_claims(self.drifted).count(), 1)

    @override_settings(OIDC_MATCH_BY_USERNAME_FALLBACK=True)
    def test_fallback_never_adopts_a_local_account_without_subject(self):
        """A break-glass account from ``createsuperuser`` has no OIDC subject;
        an IdP login with the same username must not take it over."""
        for subject in (None, ""):
            with self.subTest(subject=subject):
                User.objects.all().delete()
                User.objects.create(username="frank", subject=subject)
                claims = {**CLAIMS, "sub": f"fresh-{subject!r}"}
                self.assertEqual(self.backend.filter_users_by_claims(claims).count(), 0)
                with self.assertRaises(PermissionDenied):
                    self.backend.create_user(claims)
                self.assertEqual(User.objects.count(), 1)

    @override_settings(OIDC_MATCH_BY_USERNAME_FALLBACK=True)
    def test_fallback_leaves_a_local_superuser_untouched(self):
        User.objects.all().delete()
        root = User.objects.create_superuser(username="frank", password="pw")
        claims = {**CLAIMS, "sub": "fresh-sub"}
        self.assertEqual(self.backend.filter_users_by_claims(claims).count(), 0)
        # Nothing matched, so the OIDC flow takes the create path; the
        # username clash is rejected instead of adopting the superuser.
        with self.assertRaises(PermissionDenied):
            self.backend.create_user(claims)
        root.refresh_from_db()
        self.assertTrue(root.is_superuser)
        self.assertIsNone(root.subject)

    @override_settings(OIDC_MATCH_BY_USERNAME_FALLBACK=True)
    def test_fallback_never_adopts_an_lti_native_account(self):
        User.objects.all().delete()
        User.objects.create(username="frank", subject="lti:3:abc")
        claims = {**CLAIMS, "sub": "fresh-sub"}
        self.assertEqual(self.backend.filter_users_by_claims(claims).count(), 0)
        with self.assertLogs("basicbar_auth.oidc", level="WARNING"):
            with self.assertRaises(PermissionDenied):
                self.backend.create_user(claims)

    @override_settings(OIDC_MATCH_BY_USERNAME_FALLBACK=True)
    def test_unknown_subject_and_username_matches_nothing(self):
        stranger = {"sub": "other", "preferred_username": "someone-else"}
        self.assertEqual(self.backend.filter_users_by_claims(stranger).count(), 0)


FAILURE_URL = "http://spa.test/?sso=failed"


@requires_pyjwt
@override_settings(LOGIN_REDIRECT_URL_FAILURE=FAILURE_URL)
class LoginTokenLeewayTests(TestCase):
    """The full callback with a real RS256 ID token; only HTTP is mocked."""

    def setUp(self):
        signing = override_settings(OIDC_RP_IDP_SIGN_KEY=public_key_pem())
        signing.enable()
        self.addCleanup(signing.disable)
        session = self.client.session
        session["oidc_states"] = {"st": {"nonce": "n-1", "code_verifier": None}}
        session.save()

    def _callback(self, id_token):
        token_response = Mock(status_code=200)
        token_response.json.return_value = {"id_token": id_token, "access_token": "at"}
        userinfo = Mock(headers={"content-type": "application/json"})
        userinfo.json.return_value = CLAIMS
        jwks_response = Mock()
        jwks_response.json.return_value = jwks()

        def get(url, **kwargs):
            return jwks_response if url == "https://idp.test/jwks" else userinfo

        with (
            patch("mozilla_django_oidc.auth.requests.post", return_value=token_response),
            patch("mozilla_django_oidc.auth.requests.get", side_effect=get),
        ):
            return self.client.get(
                reverse("oidc_authentication_callback"), {"code": "c", "state": "st"}
            )

    def _id_token(self, nonce="n-1", **offsets):
        return make_token(
            {"iss": "https://idp.test", "aud": "test-client", "sub": "abc-123", "nonce": nonce},
            **offsets,
        )

    def assertLoggedIn(self, response):
        self.assertRedirects(response, "http://spa.test/", fetch_redirect_response=False)
        self.assertEqual(
            self.client.session.get("_auth_user_id"),
            str(User.objects.get(subject="abc-123").pk),
        )

    def assertRejected(self, response):
        self.assertRedirects(response, FAILURE_URL, fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_accepts_token_expired_within_leeway(self):
        self.assertLoggedIn(self._callback(self._id_token(exp_in=-10)))

    def test_login_rejects_token_expired_beyond_leeway_without_500(self):
        with self.assertLogs("basicbar_auth.oidc", level="WARNING") as logs:
            response = self._callback(self._id_token(exp_in=-120))
        self.assertRejected(response)
        self.assertEqual(
            logs.output, ["WARNING:basicbar_auth.oidc:OIDC token rejected: ExpiredSignatureError"]
        )

    def test_login_accepts_iat_slightly_in_future(self):
        self.assertLoggedIn(self._callback(self._id_token(iat_in=10)))

    def test_login_rejects_wrong_nonce(self):
        response = self._callback(self._id_token(nonce="someone-elses"))
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertFalse(User.objects.filter(subject="abc-123").exists())

    @override_settings(OIDC_TOKEN_LEEWAY=0)
    def test_leeway_setting_is_honoured(self):
        with self.assertLogs("basicbar_auth.oidc", level="WARNING"):
            self.assertRejected(self._callback(self._id_token(exp_in=-10)))

    def test_login_rejects_token_signed_by_another_key(self):
        with (
            override_settings(OIDC_RP_IDP_SIGN_KEY=public_key_pem("other")),
            self.assertLogs("basicbar_auth.oidc", level="WARNING"),
        ):
            self.assertRejected(self._callback(self._id_token()))

    @override_settings(OIDC_RP_IDP_SIGN_KEY=None)
    def test_login_via_jwks_accepts_token_expired_within_leeway(self):
        # The production path: key from the JWKS endpoint (a PyJWK).
        self.assertLoggedIn(self._callback(self._id_token(exp_in=-10)))

    @override_settings(OIDC_RP_IDP_SIGN_KEY=None)
    def test_login_via_jwks_rejects_malformed_token_without_500(self):
        # mozilla reads the header to pick the JWKS key before verifying.
        with self.assertLogs("basicbar_auth.oidc", level="WARNING") as logs:
            self.assertRejected(self._callback("not-a-jwt"))
        self.assertEqual(logs.output, ["WARNING:basicbar_auth.oidc:OIDC token rejected: DecodeError"])
