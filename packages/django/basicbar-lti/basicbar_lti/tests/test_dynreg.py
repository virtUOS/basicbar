# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Tests for LTI Dynamic Registration (token model, settings, ...)."""
import hashlib
import http.client
import io
import json
import urllib.error
import urllib.request
from datetime import timedelta
from unittest import mock

from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from basicbar_lti import conf, dynreg, dynreg_http
from basicbar_lti.dynreg_http import RegistrationError, request_json
from basicbar_lti.models import LtiPlatform, LtiRegistrationToken


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


def _addrinfo(*ips):
    return lambda host, port, *a, **kw: [
        (2, 1, 6, "", (ip, port)) for ip in ips
    ]


class _Resp:
    def __init__(self, body):
        self._body = io.BytesIO(body)

    def read(self, n=-1):
        return self._body.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class HttpClientTests(SimpleTestCase):
    def _patch(self, ip="93.184.216.34", body=b"{}"):
        gai = mock.patch("socket.getaddrinfo", side_effect=_addrinfo(ip))
        op = mock.patch.object(
            dynreg_http, "_open", return_value=_Resp(body)
        )
        return gai, op

    def test_rejects_http_by_default(self):
        gai, op = self._patch()
        with gai, op as opened:
            with self.assertRaises(RegistrationError):
                request_json("http://moodle.example.org/x")
        opened.assert_not_called()

    @override_settings(LTI_REGISTRATION_ALLOW_HTTP=True)
    def test_allow_http_setting(self):
        gai, op = self._patch(ip="127.0.0.1")
        with gai, op as opened:
            self.assertEqual(request_json("http://localhost:8000/x"), {})
        opened.assert_called_once()

    def test_rejects_loopback_link_local_unspecified(self):
        for ip in (
            "127.0.0.1",
            "::1",
            "169.254.169.254",
            "fe80::1",
            "fe80::1%eth0",
            "0.0.0.0",
            "::ffff:127.0.0.1",
        ):
            with self.subTest(ip=ip):
                gai, op = self._patch(ip=ip)
                with gai, op as opened:
                    with self.assertRaises(RegistrationError):
                        request_json("https://moodle.example.org/x")
                opened.assert_not_called()

    def test_rejects_if_any_address_bad(self):
        with mock.patch(
            "socket.getaddrinfo", side_effect=_addrinfo("93.184.216.34", "::1")
        ), mock.patch.object(dynreg_http, "_open") as opened:
            with self.assertRaises(RegistrationError):
                request_json("https://moodle.example.org/x")
        opened.assert_not_called()

    def test_resolution_failure(self):
        import socket

        with mock.patch(
            "socket.getaddrinfo", side_effect=socket.gaierror("nope")
        ), mock.patch.object(dynreg_http, "_open") as opened:
            with self.assertRaises(RegistrationError):
                request_json("https://moodle.example.org/x")
        opened.assert_not_called()

    def test_allows_private_network(self):
        gai, op = self._patch(ip="10.1.2.3", body=b'{"ok": true}')
        with gai, op as opened:
            self.assertEqual(
                request_json("https://moodle.example.org/x"), {"ok": True}
            )
        opened.assert_called_once()

    def test_bearer_and_post(self):
        gai, op = self._patch()
        with gai, op as opened:
            request_json(
                "https://moodle.example.org/x", bearer="t", payload={"a": 1}
            )
        req = opened.call_args[0][0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.get_header("Authorization"), "Bearer t")
        self.assertEqual(req.get_header("Content-type"), "application/json")
        self.assertEqual(req.get_header("Accept"), "application/json")
        self.assertEqual(json.loads(req.data), {"a": 1})

    def test_get_without_payload(self):
        gai, op = self._patch()
        with gai, op as opened:
            request_json("https://moodle.example.org/x")
        req = opened.call_args[0][0]
        self.assertEqual(req.get_method(), "GET")
        self.assertFalse(req.has_header("Authorization"))

    def test_non_json_response(self):
        gai, op = self._patch(body=b"<html>Login</html>")
        with gai, op:
            with self.assertRaises(RegistrationError) as cm:
                request_json("https://moodle.example.org/x")
        self.assertIn("JSON", str(cm.exception))

    def test_json_not_object(self):
        gai, op = self._patch(body=b"[1, 2]")
        with gai, op:
            with self.assertRaises(RegistrationError):
                request_json("https://moodle.example.org/x")

    def test_http_error_status_in_message(self):
        err = urllib.error.HTTPError(
            "https://moodle.example.org/x", 401, "Unauthorized", {},
            io.BytesIO(b"secret body " * 100),
        )
        with mock.patch(
            "socket.getaddrinfo", side_effect=_addrinfo("93.184.216.34")
        ), mock.patch.object(dynreg_http, "_open", side_effect=err):
            with self.assertRaises(RegistrationError) as cm:
                request_json("https://moodle.example.org/x")
        self.assertIn("401", str(cm.exception))
        self.assertNotIn("secret", str(cm.exception))
        self.assertIn("secret", cm.exception.detail)
        self.assertLessEqual(len(cm.exception.detail), 600)

    def test_url_error(self):
        with mock.patch(
            "socket.getaddrinfo", side_effect=_addrinfo("93.184.216.34")
        ), mock.patch.object(
            dynreg_http, "_open", side_effect=urllib.error.URLError("refused")
        ):
            with self.assertRaises(RegistrationError):
                request_json("https://moodle.example.org/x")

    def test_too_large(self):
        gai, op = self._patch(body=b" " * (dynreg_http.MAX_BYTES + 1))
        with gai, op:
            with self.assertRaises(RegistrationError):
                request_json("https://moodle.example.org/x")

    def test_cross_host_redirect_refused(self):
        handler = dynreg_http._SameOriginRedirectHandler()
        req = urllib.request.Request("https://moodle.example.org/a")
        with self.assertRaises(RegistrationError):
            handler.redirect_request(
                req, None, 302, "Found", {},
                "https://evil.example.net/b",
            )
        with self.assertRaises(RegistrationError):
            handler.redirect_request(
                req, None, 302, "Found", {},
                "http://moodle.example.org/b",
            )
        new = handler.redirect_request(
            req, None, 302, "Found", {},
            "https://moodle.example.org/b",
        )
        self.assertIsInstance(new, urllib.request.Request)
        self.assertEqual(new.full_url, "https://moodle.example.org/b")

    def test_http_exception_becomes_registration_error(self):
        with mock.patch(
            "socket.getaddrinfo", side_effect=_addrinfo("93.184.216.34")
        ), mock.patch.object(
            dynreg_http, "_open", side_effect=http.client.BadStatusLine("x")
        ):
            with self.assertRaises(RegistrationError):
                request_json("https://moodle.example.org/x")

    def test_deeply_nested_json(self):
        gai, op = self._patch(body=b"[" * 100000)
        with gai, op:
            with self.assertRaises(RegistrationError):
                request_json("https://moodle.example.org/x")

    def test_bad_port_rejected(self):
        gai, op = self._patch()
        with gai, op as opened:
            with self.assertRaises(RegistrationError):
                request_json("https://h:abc/")
        opened.assert_not_called()

    def test_userinfo_rejected(self):
        gai, op = self._patch()
        with gai, op as opened:
            with self.assertRaises(RegistrationError):
                request_json("https://u:p@moodle.example.org/x")
        opened.assert_not_called()


ISSUER = "https://moodle.example.org"
CONFIG_URL = ISSUER + "/mod/lti/openid-configuration.php"
LTI_TOOL = "https://purl.imsglobal.org/spec/lti-tool-configuration"
LTI_PLATFORM = "https://purl.imsglobal.org/spec/lti-platform-configuration"


def moodle_config(**overrides):
    config = {
        "issuer": ISSUER,
        "authorization_endpoint": ISSUER + "/mod/lti/auth.php",
        "token_endpoint": ISSUER + "/mod/lti/token.php",
        "jwks_uri": ISSUER + "/mod/lti/certs.php",
        "registration_endpoint": ISSUER + "/mod/lti/openid-registration.php",
        LTI_PLATFORM: {"product_family_code": "moodle"},
    }
    config.update(overrides)
    return config


def platform_config(**overrides):
    return dynreg.PlatformConfig(
        **{
            "issuer": ISSUER,
            "authorization_endpoint": ISSUER + "/mod/lti/auth.php",
            "token_endpoint": ISSUER + "/mod/lti/token.php",
            "jwks_uri": ISSUER + "/mod/lti/certs.php",
            "registration_endpoint": ISSUER + "/mod/lti/openid-registration.php",
            "product_family_code": "moodle",
            **overrides,
        }
    )


def secure_request():
    return RequestFactory().get("/", secure=True)


class PlatformConfigTests(SimpleTestCase):
    def load(self, config, url=CONFIG_URL, token="reg"):
        with mock.patch("basicbar_lti.dynreg.request_json", return_value=config) as m:
            result = dynreg.load_platform_config(url, token)
        m.assert_called_once_with(url, bearer=token)
        return result

    def test_config_ok(self):
        cfg = self.load(moodle_config())
        self.assertEqual(cfg, platform_config())

    def test_config_without_product_family(self):
        config = moodle_config()
        del config[LTI_PLATFORM]
        self.assertEqual(self.load(config).product_family_code, "")

    def test_config_issuer_not_prefix(self):
        with self.assertRaises(RegistrationError):
            self.load(moodle_config(), url="https://evil.example/mod/lti/x.php")

    def test_config_issuer_host_lookalike(self):
        with self.assertRaises(RegistrationError):
            self.load(
                moodle_config(),
                url="https://moodle.example.org.evil.com/mod/lti/x.php",
            )

    def test_config_issuer_path_prefix(self):
        issuer = "https://example.org/moodle"
        config = moodle_config(issuer=issuer)
        for key in (
            "authorization_endpoint",
            "token_endpoint",
            "jwks_uri",
            "registration_endpoint",
        ):
            config[key] = "https://example.org/moodle/x.php"
        self.load(config, url="https://example.org/moodle/openid-configuration.php")
        with self.assertRaises(RegistrationError):
            self.load(config, url="https://example.org/other/openid-configuration.php")

    def test_config_endpoint_other_host(self):
        with self.assertRaises(RegistrationError):
            self.load(moodle_config(jwks_uri="https://cdn.example.org/certs.php"))

    def test_config_missing_registration_endpoint(self):
        config = moodle_config()
        del config["registration_endpoint"]
        with self.assertRaises(RegistrationError):
            self.load(config)

    def test_config_overlong_values(self):
        long = ISSUER + "/" + "x" * 600
        for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
            with self.assertRaises(RegistrationError):
                self.load(moodle_config(**{key: long}))
        with self.assertRaises(RegistrationError):
            self.load(moodle_config(issuer=ISSUER + "/" + "x" * 600))

    def test_config_non_string_field(self):
        with self.assertRaises(RegistrationError):
            self.load(moodle_config(token_endpoint=5))


class PayloadTests(SimpleTestCase):
    def test_payload_shape(self):
        p = dynreg.tool_registration_payload(secure_request())
        self.assertEqual(p["application_type"], "web")
        self.assertEqual(p["response_types"], ["id_token"])
        self.assertEqual(p["grant_types"], ["implicit", "client_credentials"])
        self.assertEqual(p["token_endpoint_auth_method"], "private_key_jwt")
        self.assertEqual(p["initiate_login_uri"], "https://testserver/lti/login/")
        self.assertEqual(p["redirect_uris"], ["https://testserver/lti/launch/"])
        self.assertEqual(p["jwks_uri"], "https://testserver/lti/jwks/")
        self.assertNotIn("logo_uri", p)
        block = p[LTI_TOOL]
        self.assertEqual(block["domain"], "testserver")
        self.assertEqual(block["target_link_uri"], "https://testserver/lti/launch/")
        self.assertEqual(
            block["messages"],
            [
                {
                    "type": "LtiResourceLinkRequest",
                    "target_link_uri": "https://testserver/lti/launch/",
                }
            ],
        )
        self.assertEqual(block["claims"], conf.tool_registration()["claims"])

    @override_settings(
        LTI_TOOL_REGISTRATION={
            "client_name": "abstimmbar",
            "logo_path": "/lti/icon.svg",
            "messages": [
                {"type": "LtiResourceLinkRequest"},
                {"type": "LtiDeepLinkingRequest", "label": "Raum wählen"},
            ],
        }
    )
    def test_payload_tool_settings(self):
        p = dynreg.tool_registration_payload(secure_request())
        self.assertEqual(p["client_name"], "abstimmbar")
        self.assertEqual(p["logo_uri"], "https://testserver/lti/icon.svg")
        second = p[LTI_TOOL]["messages"][1]
        self.assertEqual(second["target_link_uri"], "https://testserver/lti/launch/")
        self.assertEqual(second["label"], "Raum wählen")

    def test_payload_refuses_http_tool_urls(self):
        with self.assertRaises(RegistrationError) as cm:
            dynreg.tool_registration_payload(RequestFactory().get("/"))
        self.assertIn("SECURE_PROXY_SSL_HEADER", str(cm.exception))

    @override_settings(LTI_REGISTRATION_ALLOW_HTTP=True)
    def test_payload_allow_http(self):
        p = dynreg.tool_registration_payload(RequestFactory().get("/"))
        self.assertEqual(p["redirect_uris"], ["http://testserver/lti/launch/"])


class RegisterTests(TestCase):
    RESPONSE = {"client_id": "abc", LTI_TOOL: {"deployment_id": "7"}}

    def register(self, token, response=None, **kw):
        with mock.patch(
            "basicbar_lti.dynreg.request_json",
            return_value=self.RESPONSE if response is None else response,
            **kw,
        ) as m:
            platform = dynreg.register_platform(
                secure_request(), token, platform_config(), "reg"
            )
        return platform, m

    def test_register_creates_platform_and_consumes_token(self):
        token, _ = LtiRegistrationToken.issue(note="Moodle Test")
        platform, m = self.register(token)
        self.assertEqual(platform.issuer, ISSUER)
        self.assertEqual(platform.client_id, "abc")
        self.assertEqual(platform.deployment_ids, ["7"])
        self.assertEqual(platform.auth_login_url, ISSUER + "/mod/lti/auth.php")
        self.assertEqual(platform.auth_token_url, ISSUER + "/mod/lti/token.php")
        self.assertEqual(platform.key_set_url, ISSUER + "/mod/lti/certs.php")
        self.assertTrue(platform.is_active)
        self.assertFalse(platform.link_by_email)
        self.assertEqual(platform.name, "Moodle Test")
        token.refresh_from_db()
        self.assertEqual(token.status, "used")
        self.assertEqual(token.platform, platform)
        args, kwargs = m.call_args
        self.assertEqual(args[0], ISSUER + "/mod/lti/openid-registration.php")
        self.assertEqual(kwargs["bearer"], "reg")
        self.assertEqual(kwargs["payload"]["application_type"], "web")

    def test_register_name_fallback(self):
        token, _ = LtiRegistrationToken.issue()
        platform, _ = self.register(token)
        self.assertEqual(platform.name, "moodle (moodle.example.org)")

    def test_register_without_deployment_id(self):
        token, _ = LtiRegistrationToken.issue()
        platform, _ = self.register(token, response={"client_id": "abc"})
        self.assertEqual(platform.deployment_ids, [])

    def test_register_lms_error_keeps_token_open(self):
        token, _ = LtiRegistrationToken.issue()
        with self.assertRaises(RegistrationError):
            self.register(token, side_effect=RegistrationError("nope"))
        self.assertEqual(LtiPlatform.objects.count(), 0)
        token.refresh_from_db()
        self.assertEqual(token.status, "open")

    def test_register_missing_client_id_keeps_token_open(self):
        token, _ = LtiRegistrationToken.issue()
        with self.assertRaises(RegistrationError):
            self.register(token, response={LTI_TOOL: {"deployment_id": "7"}})
        self.assertEqual(LtiPlatform.objects.count(), 0)
        token.refresh_from_db()
        self.assertEqual(token.status, "open")

    def test_register_overlong_client_id_keeps_token_open(self):
        token, _ = LtiRegistrationToken.issue()
        with self.assertRaises(RegistrationError):
            self.register(token, response={"client_id": "x" * 300})
        self.assertEqual(LtiPlatform.objects.count(), 0)
        token.refresh_from_db()
        self.assertEqual(token.status, "open")

    def test_register_long_fallback_name_fits(self):
        token, _ = LtiRegistrationToken.issue()
        with mock.patch(
            "basicbar_lti.dynreg.request_json", return_value=self.RESPONSE
        ):
            platform = dynreg.register_platform(
                secure_request(),
                token,
                platform_config(product_family_code="m" * 400),
                "reg",
            )
        self.assertLessEqual(len(platform.name), 200)

    def test_register_duplicate_platform_keeps_token_open(self):
        LtiPlatform.objects.create(
            name="x",
            issuer=ISSUER,
            client_id="abc",
            auth_login_url=ISSUER + "/a",
            auth_token_url=ISSUER + "/t",
        )
        token, _ = LtiRegistrationToken.issue()
        with self.assertRaises(RegistrationError):
            self.register(token)
        self.assertEqual(LtiPlatform.objects.count(), 1)
        token.refresh_from_db()
        self.assertEqual(token.status, "open")

    def test_register_used_token_refused(self):
        token, _ = LtiRegistrationToken.issue()
        LtiRegistrationToken.objects.filter(pk=token.pk).update(
            used_at=timezone.now()
        )
        with self.assertRaises(RegistrationError):
            self.register(token)
        # request_json must not have been called
        with mock.patch("basicbar_lti.dynreg.request_json") as m:
            with self.assertRaises(RegistrationError):
                dynreg.register_platform(
                    secure_request(), token, platform_config(), "reg"
                )
        m.assert_not_called()

    def test_known_issuer(self):
        cfg = platform_config()
        self.assertFalse(dynreg.known_issuer(cfg))
        platform = LtiPlatform.objects.create(
            name="x",
            issuer=ISSUER + "/",
            client_id="c",
            auth_login_url=ISSUER + "/a",
            auth_token_url=ISSUER + "/t",
            is_active=False,
        )
        self.assertFalse(dynreg.known_issuer(cfg))
        platform.is_active = True
        platform.save()
        self.assertTrue(dynreg.known_issuer(cfg))


class RegisterViewTests(TestCase):
    RESPONSE = {"client_id": "abc", LTI_TOOL: {"deployment_id": "7"}}

    def setUp(self):
        self.token, self.raw = LtiRegistrationToken.issue(note="Moodle Test")

    def params(self, **overrides):
        params = {
            "token": self.raw,
            "openid_configuration": CONFIG_URL,
            "registration_token": "rt",
        }
        params.update(overrides)
        return {k: v for k, v in params.items() if v is not None}

    def get(self, **overrides):
        return self.client.get("/lti/register/", self.params(**overrides), secure=True)

    def post(self, **overrides):
        return self.client.post(
            "/lti/register/", self.params(**overrides), secure=True
        )

    def patched(self, *side_effect):
        return mock.patch(
            "basicbar_lti.dynreg.request_json", side_effect=list(side_effect)
        )

    def test_invalid_token_403_no_request(self):
        with self.patched() as m:
            response = self.get(token="nope")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Link ungültig", response.content.decode())
        m.assert_not_called()

    def test_used_token_403_no_request(self):
        self.token.used_at = timezone.now()
        self.token.save()
        with self.patched() as m:
            response = self.get()
        self.assertEqual(response.status_code, 403)
        m.assert_not_called()

    def test_missing_openid_configuration_400(self):
        with self.patched() as m:
            response = self.get(openid_configuration=None)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Tool-URL", response.content.decode())
        m.assert_not_called()

    def test_success_creates_platform_and_closes(self):
        with self.patched(moodle_config(), self.RESPONSE) as m:
            response = self.get()
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn("org.imsglobal.lti.close", body)
        self.assertIn("Neues Fenster", body)
        self.assertEqual(m.call_count, 2)
        self.assertTrue(LtiPlatform.objects.filter(issuer=ISSUER).exists())
        self.token.refresh_from_db()
        self.assertEqual(self.token.status, "used")

    def test_success_without_deployment_warns(self):
        with self.patched(moodle_config(), {"client_id": "abc"}):
            response = self.get()
        self.assertEqual(response.status_code, 200)
        self.assertIn("Deployment-ID", response.content.decode())

    def test_success_with_deployment_has_no_warning(self):
        with self.patched(moodle_config(), self.RESPONSE):
            response = self.get()
        self.assertNotIn("Deployment-ID", response.content.decode())

    def test_config_error_502(self):
        with self.patched(RegistrationError("Konfig kaputt")) as m:
            response = self.get()
        self.assertEqual(response.status_code, 502)
        self.assertIn("Konfig kaputt", response.content.decode())
        self.assertEqual(m.call_count, 1)
        self.token.refresh_from_db()
        self.assertEqual(self.token.status, "open")

    def test_lms_error_502_token_open(self):
        with self.patched(moodle_config(), RegistrationError("LMS sagt nein")):
            response = self.get()
        self.assertEqual(response.status_code, 502)
        self.assertIn("LMS sagt nein", response.content.decode())
        self.token.refresh_from_db()
        self.assertEqual(self.token.status, "open")
        self.assertFalse(LtiPlatform.objects.exists())

    def _known(self):
        LtiPlatform.objects.create(
            name="alt",
            issuer=ISSUER,
            client_id="old",
            auth_login_url=ISSUER + "/a",
            auth_token_url=ISSUER + "/t",
        )

    def test_known_issuer_asks_first(self):
        self._known()
        with self.patched(moodle_config()) as m:
            response = self.get()
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn('name="confirm"', body)
        self.assertIn("bestehende Verknüpfung", body)
        self.assertEqual(m.call_count, 1)
        self.assertEqual(LtiPlatform.objects.count(), 1)
        self.token.refresh_from_db()
        self.assertEqual(self.token.status, "open")
        with self.patched(moodle_config(), self.RESPONSE):
            response = self.post(confirm="1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(LtiPlatform.objects.count(), 2)

    def test_post_without_confirm_asks_first(self):
        self._known()
        with self.patched(moodle_config()):
            response = self.post()
        self.assertIn('name="confirm"', response.content.decode())
        self.assertEqual(LtiPlatform.objects.count(), 1)

    def test_cancel_does_not_consume(self):
        self._known()
        with self.patched(moodle_config()):
            response = self.get()
        body = response.content.decode()
        self.assertIn("org.imsglobal.lti.close", body)
        self.assertIn('type="button"', body)
        self.assertNotIn(" onclick", body)
        self.token.refresh_from_db()
        self.assertEqual(self.token.status, "open")

    def test_values_are_escaped(self):
        evil = "<script>x</script>"
        self.token.note = evil
        self.token.save()
        with self.patched(moodle_config(), self.RESPONSE):
            ok = self.get()
        self.assertNotIn(evil, ok.content.decode())
        self.assertIn("&lt;script&gt;x&lt;/script&gt;", ok.content.decode())
        # confirm page: hidden fields and URLs
        self._known()
        with self.patched(moodle_config()):
            asks = self.get(registration_token='"><script>x</script>')
        self.assertNotIn(evil, asks.content.decode())
        # error page (the first token was consumed by the success above)
        _, self.raw = LtiRegistrationToken.issue()
        with self.patched(RegistrationError(evil)):
            err = self.get()
        self.assertNotIn(evil, err.content.decode())
        self.assertIn("&lt;script&gt;", err.content.decode())

    def test_error_is_logged(self):
        with self.patched(RegistrationError("kaputt", "detail-xyz")):
            with self.assertLogs("basicbar_lti.views", "WARNING") as logs:
                self.get()
        self.assertIn("detail-xyz", logs.output[0])


class FrameAncestorsRegisterTests(TestCase):
    def setUp(self):
        self.token, self.raw = LtiRegistrationToken.issue()

    def get(self, **overrides):
        params = {"token": self.raw, "openid_configuration": CONFIG_URL}
        params.update(overrides)
        with mock.patch(
            "basicbar_lti.dynreg.request_json",
            side_effect=[
                moodle_config(),
                {"client_id": "abc", LTI_TOOL: {"deployment_id": "7"}},
            ],
        ):
            return self.client.get("/lti/register/", params, secure=True)

    def test_valid_token_allows_config_origin(self):
        response = self.get()
        self.assertEqual(
            response["Content-Security-Policy"],
            "frame-ancestors 'self' https://moodle.example.org",
        )
        self.assertNotIn("X-Frame-Options", response)

    def test_error_page_also_allows_origin(self):
        with mock.patch(
            "basicbar_lti.dynreg.request_json", side_effect=RegistrationError("x")
        ):
            response = self.client.get(
                "/lti/register/",
                {"token": self.raw, "openid_configuration": CONFIG_URL},
                secure=True,
            )
        self.assertEqual(response.status_code, 502)
        self.assertIn("moodle.example.org", response["Content-Security-Policy"])

    def test_invalid_token_keeps_default_policy(self):
        response = self.get(token="nope")
        self.assertNotIn("moodle.example.org", response["Content-Security-Policy"])
        self.assertNotIn("X-Frame-Options", response)

    def test_invalid_origin_keeps_default_policy(self):
        response = self.get(openid_configuration="https://evil.example; x/y")
        self.assertNotIn("evil", response["Content-Security-Policy"])
        self.assertNotIn(";x", response["Content-Security-Policy"])

    def test_other_lti_pages_unchanged(self):
        response = self.client.get("/lti/page/")
        self.assertEqual(response["Content-Security-Policy"], "frame-ancestors 'self'")
        self.assertNotIn("X-Frame-Options", response)


class CheckTests(SimpleTestCase):
    def run_checks(self):
        from basicbar_lti.checks import check_registration_settings

        return check_registration_settings(None)

    @override_settings(LTI_REGISTRATION_ALLOW_HTTP=True, DEBUG=False)
    def test_w001(self):
        messages = self.run_checks()
        self.assertEqual([m.id for m in messages], ["basicbar_lti.W001"])
        self.assertIn("LTI_REGISTRATION_ALLOW_HTTP", messages[0].hint)

    @override_settings(LTI_REGISTRATION_ALLOW_HTTP=True, DEBUG=True)
    def test_no_warning_in_debug(self):
        self.assertEqual(self.run_checks(), [])

    @override_settings(LTI_REGISTRATION_ALLOW_HTTP=False, DEBUG=False)
    def test_no_warning_by_default(self):
        self.assertEqual(self.run_checks(), [])
