# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Tests for LTI Dynamic Registration (token model, settings, ...)."""
import hashlib
from datetime import timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from basicbar_lti import conf
from basicbar_lti.models import LtiRegistrationToken


class RegistrationTokenTests(TestCase):
    def test_issue_stores_only_hash(self):
        obj, raw = LtiRegistrationToken.issue(note="Moodle")
        self.assertEqual(obj.token_hash, hashlib.sha256(raw.encode()).hexdigest())
        values = [
            str(getattr(obj, f.attname)) for f in LtiRegistrationToken._meta.fields
        ]
        self.assertFalse(any(raw in v for v in values))
        self.assertEqual(obj.status, "open")

    def test_default_ttl_is_seven_days(self):
        obj, _ = LtiRegistrationToken.issue()
        delta = obj.expires_at - obj.created_at
        self.assertGreater(delta, timedelta(days=6, hours=23))
        self.assertLess(delta, timedelta(days=7, minutes=1))

    @override_settings(LTI_REGISTRATION_TOKEN_TTL=timedelta(hours=1))
    def test_ttl_setting(self):
        obj, _ = LtiRegistrationToken.issue()
        delta = obj.expires_at - obj.created_at
        self.assertGreater(delta, timedelta(minutes=59))
        self.assertLess(delta, timedelta(hours=1, minutes=1))

    def test_find_valid(self):
        obj, raw = LtiRegistrationToken.issue()
        self.assertEqual(LtiRegistrationToken.find_valid(raw), obj)
        self.assertIsNone(LtiRegistrationToken.find_valid(""))
        self.assertIsNone(LtiRegistrationToken.find_valid("nope"))
        obj.used_at = timezone.now()
        obj.save()
        self.assertIsNone(LtiRegistrationToken.find_valid(raw))
        self.assertEqual(obj.status, "used")
        obj.used_at = None
        obj.expires_at = timezone.now() - timedelta(seconds=1)
        obj.save()
        self.assertIsNone(LtiRegistrationToken.find_valid(raw))
        self.assertEqual(obj.status, "expired")

    @override_settings(LTI_TOOL_REGISTRATION={"client_name": "abstimmbar"})
    def test_tool_registration_merges_flat(self):
        cfg = conf.tool_registration()
        self.assertEqual(cfg["client_name"], "abstimmbar")
        self.assertEqual(
            cfg["claims"], conf.DEFAULTS["LTI_TOOL_REGISTRATION"]["claims"]
        )
