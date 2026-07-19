# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""LTI 1.3 machinery tests with a simulated platform (ported from abstimmbar).

The tests act as the LMS: they hold a platform RSA keypair (published to the
tool as an inline ``key_set``), run the OIDC initiation to obtain state and
nonce, then POST a properly signed ``id_token`` to the launch endpoint —
the same handshake Moodle or Stud.IP would perform. The launch endpoint here
is the minimal tool-shaped view from ``tests.urls``.
"""
import json
import time
from urllib.parse import parse_qs, urlparse

import jwt
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from jwcrypto import jwk

from basicbar_lti.models import LtiPlatform, LtiToolKey, LtiUserLink

User = get_user_model()

CLAIM = "https://purl.imsglobal.org/spec/lti/claim/"
ISSUER = "https://lms.example.edu"
CLIENT_ID = "tool-client"
DEPLOYMENT = "deployment-1"
TOOL_LAUNCH = "http://testserver/lti/launch/"


class LtiTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.platform_jwk = jwk.JWK.generate(kty="RSA", size=2048, kid="platform-key")
        cls.platform_private_pem = cls.platform_jwk.export_to_pem(
            private_key=True, password=None
        )
        public_jwk = json.loads(cls.platform_jwk.export_public())
        public_jwk.update({"alg": "RS256", "use": "sig"})
        cls.platform = LtiPlatform.objects.create(
            name="Test-LMS",
            issuer=ISSUER,
            client_id=CLIENT_ID,
            auth_login_url=f"{ISSUER}/auth",
            auth_token_url=f"{ISSUER}/token",
            key_set={"keys": [public_jwk]},
            deployment_ids=[DEPLOYMENT],
        )

    # -- the platform side of the handshake --------------------------------

    def start_login(self, target=TOOL_LAUNCH):
        """OIDC initiation → returns (state, nonce, redirect_uri)."""
        response = self.client.post(
            "/lti/login/",
            {
                "iss": ISSUER,
                "client_id": CLIENT_ID,
                "login_hint": "user-1",
                "target_link_uri": target,
                "lti_message_hint": "hint",
            },
        )
        self.assertEqual(response.status_code, 302, response.content)
        query = parse_qs(urlparse(response["Location"]).query)
        self.assertEqual(query["client_id"][0], CLIENT_ID)
        self.assertEqual(query["redirect_uri"][0], target)
        return query["state"][0], query["nonce"][0], query["redirect_uri"][0]

    def make_id_token(self, nonce, message_type="LtiResourceLinkRequest",
                      roles=None, extra=None, sub="user-1"):
        now = int(time.time())
        payload = {
            "iss": ISSUER,
            "aud": CLIENT_ID,
            "sub": sub,
            "iat": now,
            "exp": now + 300,
            "nonce": nonce,
            "given_name": "Frank",
            "family_name": "Lehrender",
            "email": "frank@lms.example.edu",
            f"{CLAIM}message_type": message_type,
            f"{CLAIM}version": "1.3.0",
            f"{CLAIM}deployment_id": DEPLOYMENT,
            f"{CLAIM}target_link_uri": TOOL_LAUNCH,
            f"{CLAIM}roles": roles if roles is not None else [
                "http://purl.imsglobal.org/vocab/lis/v2/membership#Instructor"
            ],
            f"{CLAIM}context": {"id": "course-42", "title": "Bio 101 (LMS)"},
        }
        if message_type == "LtiResourceLinkRequest":
            payload[f"{CLAIM}resource_link"] = {"id": "link-1"}
        if extra:
            payload.update(extra)
        return jwt.encode(
            payload,
            self.platform_private_pem,
            algorithm="RS256",
            headers={"kid": "platform-key"},
        )

    def launch(self, **token_kwargs):
        state, nonce, redirect_uri = self.start_login()
        id_token = self.make_id_token(nonce, **token_kwargs)
        return self.client.post(redirect_uri, {"state": state, "id_token": id_token})


class LoginTests(LtiTestCase):
    def test_login_redirects_to_platform_auth(self):
        state, nonce, _ = self.start_login()
        self.assertTrue(state and nonce)

    def test_login_requires_target(self):
        response = self.client.post("/lti/login/", {"iss": ISSUER})
        self.assertEqual(response.status_code, 400)


class HandshakeTests(LtiTestCase):
    def test_instructor_launch_provisions_user(self):
        response = self.launch()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["instructor"])
        user = User.objects.get(subject=f"lti:{self.platform.pk}:user-1")
        self.assertEqual(user.first_name, "Frank")
        self.assertEqual(
            LtiUserLink.objects.get(platform=self.platform, sub="user-1").user, user
        )

    def test_second_launch_reuses_user(self):
        self.launch()
        self.launch()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(LtiUserLink.objects.count(), 1)

    def test_learner_gets_no_account(self):
        response = self.launch(
            roles=["http://purl.imsglobal.org/vocab/lis/v2/membership#Learner"],
            sub="student-9",
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["instructor"])
        self.assertEqual(User.objects.count(), 0)

    def test_tampered_token_is_rejected(self):
        state, nonce, redirect_uri = self.start_login()
        foreign_key = jwk.JWK.generate(kty="RSA", size=2048, kid="platform-key")
        evil = jwt.encode(
            {"iss": ISSUER, "aud": CLIENT_ID, "nonce": nonce,
             "iat": int(time.time()), "exp": int(time.time()) + 300,
             f"{CLAIM}message_type": "LtiResourceLinkRequest",
             f"{CLAIM}version": "1.3.0",
             f"{CLAIM}deployment_id": DEPLOYMENT},
            foreign_key.export_to_pem(private_key=True, password=None),
            algorithm="RS256",
            headers={"kid": "platform-key"},
        )
        with self.assertRaises(Exception):
            self.client.post(redirect_uri, {"state": state, "id_token": evil})

    def test_unknown_deployment_is_rejected(self):
        with self.assertRaises(Exception):
            self.launch(extra={f"{CLAIM}deployment_id": "other-deployment"})


class JwksTests(LtiTestCase):
    def test_jwks_serves_tool_public_key(self):
        response = self.client.get("/lti/jwks/")
        self.assertEqual(response.status_code, 200)
        keys = response.json()["keys"]
        self.assertEqual(keys[0]["kty"], "RSA")
        # Key is persisted — the endpoint must be stable across requests.
        self.assertEqual(LtiToolKey.objects.count(), 1)
        self.assertEqual(self.client.get("/lti/jwks/").json(), response.json())


class AccountLinkingTests(LtiTestCase):
    """LTI and OIDC logins should map onto the same user.

    The launch id_token carries email frank@lms.example.edu (see
    make_id_token); linking is an opt-in per platform.
    """

    def oidc_user(self, email="frank@lms.example.edu", **kwargs):
        return User.objects.create_user(
            username=kwargs.pop("username", "frank"),
            email=email,
            subject=kwargs.pop("subject", "keycloak-sub-1"),
            **kwargs,
        )

    def enable_linking(self):
        self.platform.link_by_email = True
        self.platform.save()

    def test_off_by_default_creates_separate_user(self):
        self.oidc_user()
        self.launch()
        self.assertEqual(User.objects.count(), 2)

    def test_link_by_email_reuses_oidc_user(self):
        user = self.oidc_user()
        self.enable_linking()
        response = self.launch()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.count(), 1)
        link = LtiUserLink.objects.get(platform=self.platform, sub="user-1")
        self.assertEqual(link.user, user)

    def test_linked_oidc_profile_is_not_clobbered(self):
        user = self.oidc_user(first_name="Franziska", last_name="Original")
        self.enable_linking()
        self.launch()
        user.refresh_from_db()
        # The IdP stays the source of truth for linked accounts.
        self.assertEqual(user.subject, "keycloak-sub-1")
        self.assertEqual(user.username, "frank")
        self.assertEqual(user.first_name, "Franziska")
        self.assertEqual(user.last_name, "Original")

    def test_email_match_is_case_insensitive(self):
        user = self.oidc_user(email="Frank@LMS.Example.EDU")
        self.enable_linking()
        self.launch()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(LtiUserLink.objects.get().user, user)

    def test_link_survives_later_email_change(self):
        user = self.oidc_user()
        self.enable_linking()
        self.launch()
        user.email = "frank.neu@uni.example"
        user.save()
        self.launch()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(LtiUserLink.objects.count(), 1)

    def test_ambiguous_email_creates_new_user(self):
        self.oidc_user()
        self.oidc_user(username="frank2", subject="keycloak-sub-2")
        self.enable_linking()
        self.launch()
        # Two candidates → no auto-link, a fresh LTI user instead.
        self.assertEqual(User.objects.count(), 3)
        link = LtiUserLink.objects.get()
        self.assertTrue(link.user.subject.startswith("lti:"))

    def test_empty_email_creates_new_user(self):
        self.oidc_user()
        self.enable_linking()
        self.launch(extra={"email": ""})
        self.assertEqual(User.objects.count(), 2)

    def test_legacy_lti_user_is_adopted_into_link_table(self):
        legacy = User.objects.create_user(
            username="lti-old",
            subject=f"lti:{self.platform.pk}:user-1",
            email="frank@lms.example.edu",
        )
        self.enable_linking()
        self.launch()
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(LtiUserLink.objects.get().user, legacy)
        legacy.refresh_from_db()
        # LTI-native profiles keep updating from the launch.
        self.assertEqual(legacy.first_name, "Frank")


class LtiPlatformApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="chef", is_staff=True)
        self.user = User.objects.create_user(username="teacher")
        self.payload = {
            "name": "Moodle Test",
            "issuer": "https://moodle.example.org",
            "client_id": "abc123",
            "auth_login_url": "https://moodle.example.org/mod/lti/auth.php",
            "auth_token_url": "https://moodle.example.org/mod/lti/token.php",
            "key_set_url": "https://moodle.example.org/mod/lti/certs.php",
            "deployment_ids": ["1", "2"],
            "link_by_email": True,
            "is_active": True,
        }

    def test_requires_admin(self):
        # anonymous
        self.assertEqual(self.client.get("/api/lti/platforms/").status_code, 403)
        # non-staff
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/api/lti/platforms/").status_code, 403)

    def test_admin_crud_and_no_key_material_in_payload(self):
        self.client.force_login(self.admin)
        resp = self.client.post("/api/lti/platforms/", self.payload,
                                content_type="application/json")
        self.assertEqual(resp.status_code, 201, resp.content)
        body = resp.json()
        self.assertEqual(body["deployment_ids"], ["1", "2"])
        self.assertNotIn("private_key", body)
        self.assertNotIn("key_set", body)
        pk = body["id"]
        # list (no global pagination in the package test settings → bare list)
        self.assertEqual(len(self.client.get("/api/lti/platforms/").json()), 1)
        # update
        r = self.client.patch(f"/api/lti/platforms/{pk}/", {"is_active": False},
                              content_type="application/json")
        self.assertFalse(r.json()["is_active"])
        # delete
        self.assertEqual(
            self.client.delete(f"/api/lti/platforms/{pk}/").status_code, 204)

    def test_duplicate_issuer_client_id_is_400_not_500(self):
        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.post("/api/lti/platforms/", self.payload,
                             content_type="application/json").status_code, 201)
        dup = self.client.post("/api/lti/platforms/", self.payload,
                               content_type="application/json")
        self.assertEqual(dup.status_code, 400)

    def test_deployment_ids_strips_blanks(self):
        self.client.force_login(self.admin)
        p = {**self.payload, "deployment_ids": ["1", "", "  ", "2"]}
        resp = self.client.post("/api/lti/platforms/", p,
                                content_type="application/json")
        self.assertEqual(resp.json()["deployment_ids"], ["1", "2"])

    def test_tool_info_admin_only_and_urls(self):
        self.assertEqual(self.client.get("/api/lti/tool-info/").status_code, 403)
        self.client.force_login(self.admin)
        info = self.client.get("/api/lti/tool-info/").json()
        self.assertTrue(info["login_url"].endswith("/lti/login/"))
        self.assertTrue(info["launch_url"].endswith("/lti/launch/"))
        self.assertTrue(info["jwks_url"].endswith("/lti/jwks/"))
        self.assertTrue(info["icon_url"].endswith("/lti/icon.svg"))

    def test_created_platform_appears_in_jwks(self):
        from basicbar_lti.tool_conf import build_tool_conf

        self.client.force_login(self.admin)
        self.client.post("/api/lti/platforms/", self.payload,
                         content_type="application/json")
        jwks = build_tool_conf().get_jwks()
        self.assertTrue(jwks.get("keys"))  # key now served for the registration


class LtiFrameAncestorsTests(TestCase):
    """The frame-ancestors middleware, exercised on the /lti/ test page."""

    def _html(self):
        return self.client.get("/lti/page/")

    def test_no_platform_only_self(self):
        resp = self._html()
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("X-Frame-Options", resp)
        self.assertIn("frame-ancestors 'self'", resp["Content-Security-Policy"])
        # no external origin when no platform registered
        self.assertNotIn(
            "http", resp["Content-Security-Policy"].split("frame-ancestors")[1]
        )

    def test_active_platform_origin_allowed(self):
        LtiPlatform.objects.create(
            name="M", issuer="https://moodle.example.org/", client_id="c",
            auth_login_url="https://moodle.example.org/auth",
            auth_token_url="https://moodle.example.org/tok", is_active=True,
        )
        csp = self._html()["Content-Security-Policy"]
        self.assertIn("frame-ancestors 'self' https://moodle.example.org", csp)
        # scheme+host only, no path/trailing slash
        self.assertNotIn("moodle.example.org/auth", csp)

    def test_inactive_platform_not_allowed(self):
        LtiPlatform.objects.create(
            name="M", issuer="https://inactive.example.org", client_id="c",
            auth_login_url="https://inactive.example.org/a",
            auth_token_url="https://inactive.example.org/t", is_active=False,
        )
        csp = self._html()["Content-Security-Policy"]
        self.assertNotIn("inactive.example.org", csp)

    def test_path_outside_prefixes_keeps_deny(self):
        from django.http import HttpResponse
        from django.test import RequestFactory

        from basicbar_lti.middleware import LtiFrameAncestorsMiddleware

        request = RequestFactory().get("/admin/")

        def get_response(_request):
            resp = HttpResponse(content_type="text/html")
            resp["X-Frame-Options"] = "DENY"
            return resp

        response = LtiFrameAncestorsMiddleware(get_response)(request)
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertNotIn("Content-Security-Policy", response)

    @override_settings(LTI_FRAME_PATH_PREFIXES=("/lti/", "/p/"))
    def test_prefixes_are_configurable(self):
        from django.http import HttpResponse
        from django.test import RequestFactory

        from basicbar_lti.middleware import LtiFrameAncestorsMiddleware

        request = RequestFactory().get("/p/abc/")

        def get_response(_request):
            return HttpResponse(content_type="text/html")

        response = LtiFrameAncestorsMiddleware(get_response)(request)
        self.assertIn("frame-ancestors", response["Content-Security-Policy"])

    def test_malicious_issuer_not_injected(self):
        LtiPlatform.objects.create(
            name="Evil", issuer="https://evil.example.org;style-src *", client_id="c1",
            auth_login_url="https://evil.example.org/auth",
            auth_token_url="https://evil.example.org/tok", is_active=True,
        )
        LtiPlatform.objects.create(
            name="Evil2", issuer="https://a.example.org b.example.org", client_id="c2",
            auth_login_url="https://a.example.org/auth",
            auth_token_url="https://a.example.org/tok", is_active=True,
        )
        LtiPlatform.objects.create(
            name="Good", issuer="https://good.example.org", client_id="c3",
            auth_login_url="https://good.example.org/auth",
            auth_token_url="https://good.example.org/tok", is_active=True,
        )
        csp = self._html()["Content-Security-Policy"]
        self.assertNotIn("style-src", csp)
        self.assertNotIn(";", csp)
        self.assertNotIn("evil.example.org", csp)
        self.assertNotIn("a.example.org", csp)
        self.assertNotIn("b.example.org", csp)
        self.assertIn("frame-ancestors 'self' https://good.example.org", csp)
