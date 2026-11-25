# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Tests for LTI Dynamic Registration (token model, settings, ...)."""
import hashlib
import io
import json
import urllib.error
import urllib.request
from datetime import timedelta
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from basicbar_lti import conf, dynreg_http
from basicbar_lti.dynreg_http import RegistrationError, request_json
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
