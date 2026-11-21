# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from unittest import mock
from urllib.parse import parse_qs

import httpx
from django.test import SimpleTestCase

from basicbar_integrations import gitlab
from basicbar_integrations.gitlab import GitLabError, Issue

TOKEN = "glpat-secret-token-123"
BODY_MARK = "BODY-MARKER-do-not-leak"
URL = "https://git.example.org/group/sub/project"


def transport(handler):
    return mock.patch.object(gitlab, "_transport", httpx.MockTransport(handler))


def form(request):
    return {k: v[0] for k, v in parse_qs(request.content.decode()).items()}


class ParseProjectUrlTests(SimpleTestCase):
    def test_parse_project_url(self):
        host = "https://git.example.org"
        for url, expected in [
            (URL, (host, "group/sub/project")),
            ("https://git.example.org/g/p.git", (host, "g/p")),
            ("https://git.example.org/g/p/-/issues?x=1#y", (host, "g/p")),
            ("https://git.example.org/g/p?x=1#y", (host, "g/p")),
            ("https://git.example.org:8443/g/p/", (host + ":8443", "g/p")),
            ("  https://git.example.org/g/p  ", (host, "g/p")),
        ]:
            with self.subTest(url=url):
                self.assertEqual(gitlab.parse_project_url(url), expected)

    def test_parse_rejects(self):
        for url in (
            "",
            "http://git.example.org/g/p",
            "ftp://git.example.org/g/p",
            "https://u:p@git.example.org/g/p",
            "https://u@git.example.org/g/p",
            "https://git.example.org",
            "https://git.example.org/",
            "https://git.example.org/-/issues",
            "https://git.example.org:99999999/g/p",
            "https://git.example.org/.git",
            "not a url",
        ):
            with self.subTest(url=url):
                self.assertIsNone(gitlab.parse_project_url(url))

    def test_parse_strips_slash_left_by_git_suffix(self):
        self.assertEqual(
            gitlab.parse_project_url("https://git.example.org/g/.git"), ("https://git.example.org", "g")
        )

    def test_parse_allows_http_when_asked(self):
        self.assertEqual(
            gitlab.parse_project_url("http://localhost:8929/g/p", allow_http=True),
            ("http://localhost:8929", "g/p"),
        )
        self.assertIsNone(gitlab.parse_project_url("ftp://localhost/g/p", allow_http=True))
        self.assertIsNone(gitlab.parse_project_url("http://u:p@localhost/g/p", allow_http=True))


class SameOriginTests(SimpleTestCase):
    def test_same_origin(self):
        same = [
            ("https://a.example/x", "https://a.example/y"),
            ("https://a.example:443/x", "https://a.example/y"),
            ("http://a.example:80/x", "http://a.example/y"),
            ("HTTPS://A.Example/x", "https://a.example/y"),
        ]
        different = [
            ("https://a.example:8443/x", "https://a.example/y"),
            ("http://a.example/x", "https://a.example/y"),
            ("https://a.example/x", "https://b.example/y"),
            ("https://a.example:80/x", "https://a.example/y"),
            ("https://evil.example\\@a.example/x", "https://a.example/y"),
            ("https://u@a.example/x", "https://a.example/y"),
        ]
        for a, b in same:
            with self.subTest(a=a, b=b):
                self.assertTrue(gitlab.same_origin(a, b))
        for a, b in different:
            with self.subTest(a=a, b=b):
                self.assertFalse(gitlab.same_origin(a, b))
        for a, b in [("", ""), ("not a url", "not a url"), ("https://a.example:abc/x", "https://a.example/")]:
            with self.subTest(a=a, b=b):
                self.assertFalse(gitlab.same_origin(a, b))


class CreateIssueTests(SimpleTestCase):
    def test_create_issue_sends_token_header_and_fields(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(201, json={"iid": 17, "web_url": f"{URL}/-/issues/17"})

        with transport(handler):
            issue = gitlab.create_issue(URL, TOKEN, title="Titel", description="Beschreibung")
        self.assertEqual(issue, Issue(iid=17, web_url=f"{URL}/-/issues/17"))
        (request,) = seen
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url.host, "git.example.org")
        self.assertEqual(request.url.raw_path, b"/api/v4/projects/group%2Fsub%2Fproject/issues")
        self.assertEqual(request.headers["PRIVATE-TOKEN"], TOKEN)
        self.assertNotIn(TOKEN, str(request.url))
        self.assertNotIn(TOKEN.encode(), request.content)
        self.assertEqual(form(request), {"title": "Titel", "description": "Beschreibung"})

    def test_create_issue_confidential_and_labels(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(201, json={"iid": 3, "confidential": True})

        with transport(handler):
            issue = gitlab.create_issue(
                URL, TOKEN, title="T", description="D", confidential=True, labels=["a", "b"]
            )
        self.assertEqual(issue.iid, 3)
        self.assertEqual(
            form(seen[0]),
            {"title": "T", "description": "D", "confidential": "true", "labels": "a,b"},
        )

    def test_confidential_not_confirmed_raises(self):
        for body in ({"iid": 3}, {"iid": 3, "confidential": False}, {"iid": 3, "confidential": "true"}):
            with self.subTest(body=body):
                with transport(lambda request, body=body: httpx.Response(201, json=body)):
                    with self.assertRaises(GitLabError):
                        gitlab.create_issue(URL, TOKEN, title="T", description="D", confidential=True)

    def test_confidential_with_non_json_raises(self):
        for response in (
            httpx.Response(201, text="<html>ok</html>"),
            httpx.Response(201, json=["not", "a", "dict"]),
        ):
            with self.subTest(response=response.text):
                with transport(lambda request, response=response: response):
                    with self.assertRaises(GitLabError):
                        gitlab.create_issue(URL, TOKEN, title="T", description="D", confidential=True)

    def test_issue_without_iid_is_returned_as_none(self):
        for response in (
            httpx.Response(201, json={}),
            httpx.Response(201, json={"iid": 0}),
            httpx.Response(201, json={"iid": "7"}),
            httpx.Response(201, json={"iid": True}),
            httpx.Response(201, json=[1]),
            httpx.Response(201, text="not json"),
        ):
            with self.subTest(response=response.text):
                with transport(lambda request, response=response: response):
                    issue = gitlab.create_issue(URL, TOKEN, title="T", description="D")
                self.assertEqual(issue, Issue(iid=None, web_url=None))

    def test_web_url_only_on_same_origin(self):
        def issue_for(web_url):
            with transport(lambda request: httpx.Response(201, json={"iid": 1, "web_url": web_url})):
                return gitlab.create_issue(URL, TOKEN, title="T", description="D")

        ok = "https://git.example.org/group/sub/project/-/issues/1"
        self.assertEqual(issue_for(ok).web_url, ok)
        self.assertEqual(issue_for(f"  {ok}  ").web_url, ok)
        explicit_port = "https://git.example.org:443/group/sub/project/-/issues/1"
        self.assertEqual(issue_for(explicit_port).web_url, explicit_port)
        for bad in (
            "https://evil.example/group/sub/project/-/issues/1",
            "javascript:alert(1)",
            "http://git.example.org/group/sub/project/-/issues/1",
            "https://git.example.org:8443/x",
            "https://evil.example\\@git.example.org/x",
            "https://u@git.example.org/x",
            "https://[evil/x",
            "https://[notipv6]/x",
            42,
            None,
            "",
        ):
            with self.subTest(web_url=bad):
                issue = issue_for(bad)
                self.assertEqual(issue.iid, 1)
                self.assertIsNone(issue.web_url)

    def test_allow_http_reaches_http_projects(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(201, json={"iid": 2, "web_url": "http://localhost:8929/g/p/-/issues/2"})

        with transport(handler):
            issue = gitlab.create_issue(
                "http://localhost:8929/g/p", TOKEN, title="T", description="D", allow_http=True
            )
        self.assertEqual(seen[0].url.scheme, "http")
        self.assertEqual(issue.web_url, "http://localhost:8929/g/p/-/issues/2")


class ErrorTests(SimpleTestCase):
    def test_redirect_is_not_followed(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(302, headers={"Location": "https://evil.example/steal"})

        with transport(handler):
            with self.assertRaises(GitLabError) as ctx:
                gitlab.create_issue(URL, TOKEN, title="T", description="D")
        self.assertIn("302", str(ctx.exception))
        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0].url.host, "git.example.org")

    def test_non_2xx_raises_with_status_only(self):
        with transport(lambda request: httpx.Response(500, text=BODY_MARK)):
            with self.assertRaises(GitLabError) as ctx:
                gitlab.create_issue(URL, TOKEN, title="T", description="D")
        self.assertEqual(str(ctx.exception), "GitLab answered HTTP 500")

    def test_unreachable_raises_with_class_name_only(self):
        def handler(request):
            raise httpx.ConnectError(f"boom {TOKEN} {BODY_MARK}")

        with transport(handler):
            with self.assertRaises(GitLabError) as ctx:
                gitlab.create_issue(URL, TOKEN, title="T", description="D")
        self.assertEqual(str(ctx.exception), "GitLab unreachable (ConnectError)")

    def _error_paths(self):
        """Callables that each end in a GitLabError, with a token and body-carrying server."""
        def call(handler, fn):
            def run():
                with transport(handler):
                    fn()
            return run

        create = lambda **kw: gitlab.create_issue(URL, TOKEN, title="T", description="D", **kw)
        upload = lambda: gitlab.upload_file(
            URL, TOKEN, filename="a.png", data=b"x", content_type="image/png"
        )

        def boom(request):
            raise httpx.ReadTimeout(f"{TOKEN} {BODY_MARK}")

        return [
            call(lambda r: httpx.Response(500, text=f"{TOKEN} {BODY_MARK}"), create),
            call(lambda r: httpx.Response(302, headers={"Location": f"https://x/{BODY_MARK}"}), create),
            call(boom, create),
            call(lambda r: httpx.Response(201, text=f"{TOKEN} {BODY_MARK}"),
                 lambda: create(confidential=True)),
            call(lambda r: httpx.Response(201, json={"confidential": False, "note": BODY_MARK}),
                 lambda: create(confidential=True)),
            call(lambda r: httpx.Response(201, json={"note": BODY_MARK}), upload),
            call(lambda r: httpx.Response(404, text=BODY_MARK), upload),
            call(boom, upload),
        ]

    def test_errors_never_contain_token_or_body(self):
        for run in self._error_paths():
            with self.assertRaises(GitLabError) as ctx:
                run()
            self.assertNotIn(TOKEN, str(ctx.exception))
            self.assertNotIn(BODY_MARK, str(ctx.exception))
            # No chained original exception (it could carry the token or body).
            self.assertTrue(ctx.exception.__suppress_context__ or ctx.exception.__context__ is None)
            self.assertIsNone(ctx.exception.__cause__)

    def test_unsendable_request_raises_gitlab_error_without_token_char(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={})

        with transport(handler):
            for url, token in [(URL, "glpat-\u00e4"), ("https://xn--a.org/g/p", "glpat-x")]:
                with self.subTest(url=url):
                    for fn in (
                        lambda: gitlab.create_issue(url, token, title="T", description="D"),
                        lambda: gitlab.upload_file(url, token, filename="a", data=b"", content_type="x/y"),
                    ):
                        with self.assertRaises(GitLabError) as ctx:
                            fn()
                        self.assertNotIn("\u00e4", str(ctx.exception))
                        self.assertNotIn("position", str(ctx.exception))
                        self.assertRegex(str(ctx.exception), r"^GitLab request could not be sent \(\w+\)$")
                        self.assertNotIn("unreachable", str(ctx.exception))
                    self.assertFalse(gitlab.check_project(url, token))

    def test_labels_must_not_be_a_plain_string(self):
        with self.assertRaises(TypeError):
            gitlab.create_issue(URL, TOKEN, title="T", description="D", labels="bug")

    def test_not_configured_sends_nothing(self):
        calls = []

        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={})

        cases = [
            (URL, ""),
            ("", TOKEN),
            ("http://git.example.org/g/p", TOKEN),
            ("https://user:pw@git.example.org/g/p", TOKEN),
            ("https://git.example.org", TOKEN),
        ]
        with transport(handler):
            for url, token in cases:
                with self.subTest(url=url, token=bool(token)):
                    with self.assertRaisesMessage(GitLabError, "GitLab is not configured correctly"):
                        gitlab.create_issue(url, token, title="T", description="D")
                    with self.assertRaisesMessage(GitLabError, "GitLab is not configured correctly"):
                        gitlab.upload_file(url, token, filename="a", data=b"", content_type="x/y")
                    self.assertFalse(gitlab.check_project(url, token))
        self.assertEqual(calls, [])

    def test_module_does_not_log(self):
        # httpx itself logs requests at INFO on its own logger; the package must add nothing.
        with self.assertNoLogs("basicbar_integrations", level="DEBUG"):
            for run in self._error_paths():
                with self.assertRaises(GitLabError):
                    run()
            with transport(lambda r: httpx.Response(200, json={})):
                gitlab.check_project(URL, TOKEN)
            gitlab.check_project("", "")


class UploadTests(SimpleTestCase):
    def test_upload_file_returns_markdown(self):
        seen = []

        def handler(request):
            seen.append(request)
            return httpx.Response(201, json={"markdown": "![a](/uploads/x/a.png)"})

        with transport(handler):
            markdown = gitlab.upload_file(
                URL, TOKEN, filename="shot.png", data=b"PNGDATA", content_type="image/png"
            )
        self.assertEqual(markdown, "![a](/uploads/x/a.png)")
        (request,) = seen
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url.raw_path, b"/api/v4/projects/group%2Fsub%2Fproject/uploads")
        self.assertEqual(request.headers["PRIVATE-TOKEN"], TOKEN)
        self.assertTrue(request.headers["Content-Type"].startswith("multipart/form-data"))
        self.assertIn(b'filename="shot.png"', request.content)
        self.assertIn(b"Content-Type: image/png", request.content)
        self.assertIn(b"PNGDATA", request.content)
        self.assertNotIn(TOKEN.encode(), request.content)

    def test_upload_without_markdown_raises(self):
        for response in (
            httpx.Response(201, json={}),
            httpx.Response(201, json={"markdown": ""}),
            httpx.Response(201, json={"markdown": 5}),
            httpx.Response(201, text="nope"),
        ):
            with self.subTest(response=response.text):
                with transport(lambda request, response=response: response):
                    with self.assertRaises(GitLabError):
                        gitlab.upload_file(
                            URL, TOKEN, filename="a.png", data=b"x", content_type="image/png"
                        )


class CheckProjectTests(SimpleTestCase):
    def test_check_project_true_on_200_false_otherwise(self):
        seen = []

        def ok(request):
            seen.append(request)
            return httpx.Response(200, json={"id": 1})

        with transport(ok):
            self.assertTrue(gitlab.check_project(URL, TOKEN))
        (request,) = seen
        self.assertEqual(request.method, "GET")
        self.assertEqual(request.url.raw_path, b"/api/v4/projects/group%2Fsub%2Fproject")
        self.assertEqual(request.headers["PRIVATE-TOKEN"], TOKEN)

        def unreachable(request):
            raise httpx.ConnectError("down")

        for handler in (
            lambda r: httpx.Response(401),
            lambda r: httpx.Response(404),
            lambda r: httpx.Response(302, headers={"Location": "https://evil.example/"}),
            unreachable,
        ):
            with transport(handler):
                self.assertFalse(gitlab.check_project(URL, TOKEN))
