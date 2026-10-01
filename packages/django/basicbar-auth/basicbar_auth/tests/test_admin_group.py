# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""IdP-group → Django-admin mapping (ported from ausleihbar)."""
from django.test import TestCase, override_settings

from basicbar_auth.oidc import OIDCBackend, claims_in_admin_group, is_oidc_admin


@override_settings(OIDC_ADMIN_GROUP="tool-admins", OIDC_GROUPS_CLAIM="groups")
class OIDCAdminGroupTests(TestCase):
    def setUp(self):
        self.backend = OIDCBackend()

    def test_admin_group_grants_staff_and_superuser(self):
        user = self.backend.create_user(
            {"sub": "a1", "preferred_username": "boss", "groups": ["tool-admins"]}
        )
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(is_oidc_admin(user))

    def test_non_admin_group_has_no_admin(self):
        user = self.backend.create_user(
            {"sub": "a2", "preferred_username": "student", "groups": ["students"]}
        )
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(is_oidc_admin(user))

    def test_full_group_path_still_grants_admin(self):
        # Keycloak with "Full group path" on sends a leading-slash path.
        user = self.backend.create_user(
            {"sub": "a4", "preferred_username": "boss2", "groups": ["/tool-admins"]}
        )
        self.assertTrue(user.is_superuser)

    def test_nested_group_path_grants_admin(self):
        user = self.backend.create_user(
            {"sub": "a5", "preferred_username": "boss3", "groups": ["/staff/tool-admins"]}
        )
        self.assertTrue(user.is_superuser)

    def test_group_membership_is_authoritative_on_update(self):
        user = self.backend.create_user(
            {"sub": "a3", "preferred_username": "x", "groups": ["tool-admins"]}
        )
        self.assertTrue(user.is_superuser)
        # Removed from the admin group -> admin revoked.
        self.backend.update_user(user, {"sub": "a3", "groups": []})
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertFalse(is_oidc_admin(user))

    def test_local_promotion_survives_a_login_without_the_group(self):
        # Promoted inside the tool (user management / Django admin), never a
        # member of the IdP group: the next login must not demote them.
        user = self.backend.create_user(
            {"sub": "a6", "preferred_username": "local", "groups": ["students"]}
        )
        user.is_staff = user.is_superuser = True
        user.save()
        self.backend.update_user(user, {"sub": "a6", "groups": ["students"]})
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        # … and the tool may still revoke it locally: it is not an IdP admin.
        self.assertFalse(is_oidc_admin(user))

    def test_joining_the_group_later_grants_admin(self):
        user = self.backend.create_user({"sub": "a7", "preferred_username": "y", "groups": []})
        self.assertFalse(user.is_staff)
        self.backend.update_user(user, {"sub": "a7", "groups": ["tool-admins"]})
        user.refresh_from_db()
        self.assertTrue(user.is_superuser)
        self.assertTrue(is_oidc_admin(user))


class NoAdminGroupConfiguredTests(TestCase):
    def test_without_admin_group_nothing_is_granted(self):
        self.assertFalse(claims_in_admin_group({"groups": ["anything"]}))
        user = OIDCBackend().create_user(
            {"sub": "n1", "preferred_username": "n", "groups": ["anything"]}
        )
        self.assertFalse(user.is_staff)
