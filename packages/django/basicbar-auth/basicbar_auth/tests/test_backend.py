# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Claim mapping, account cap and subject handling (ported from the tools)."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase, override_settings
from django.utils import timezone

from basicbar_auth.oidc import OIDCBackend

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
        matched = self.backend.filter_users_by_claims(self.drifted)
        self.assertEqual(list(matched), [self.user])
        # update_user adopts the new subject, so the next login matches
        # directly again.
        updated = self.backend.update_user(self.user, self.drifted)
        self.assertEqual(updated.subject, "new-sub-456")
        self.assertEqual(self.backend.filter_users_by_claims(self.drifted).count(), 1)

    @override_settings(OIDC_MATCH_BY_USERNAME_FALLBACK=True)
    def test_unknown_subject_and_username_matches_nothing(self):
        stranger = {"sub": "other", "preferred_username": "someone-else"}
        self.assertEqual(self.backend.filter_users_by_claims(stranger).count(), 0)
