# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Minimal GitLab client: check a project, upload a file, create an issue.

Needs the extra ``basicbar-integrations[gitlab]`` (``httpx``). Only
``GET .../projects/:id``, ``POST .../uploads`` and ``POST .../issues`` are sent, to exactly
the configured host, without following redirects. Privacy: the token travels only in the
``PRIVATE-TOKEN`` header; ``GitLabError`` messages carry a status code or an exception class
name, never the token, a response body or any issue content. The module does not log.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import quote, urlsplit

import httpx

TIMEOUT_SECONDS = 15


class GitLabError(Exception):
    """A GitLab problem; the message never contains the token or any content."""


@dataclass(frozen=True)
class Issue:
    iid: int | None
    web_url: str | None


# Test seam: an httpx transport (e.g. httpx.MockTransport); None means the real network.
_transport: httpx.BaseTransport | None = None


def parse_project_url(url: str, *, allow_http: bool = False) -> tuple[str, str] | None:
    """``https://host[:port]/g/sub/p[.git][/-/...]`` -> ``("https://host[:port]", "g/sub/p")``.

    Query, fragment, a ``.git`` suffix and a ``/-/`` tail are dropped. Anything but https
    (http only with ``allow_http``), URLs with userinfo and URLs without a project path give None.
    """
    try:
        parts = urlsplit((url or "").strip())
        host = parts.hostname
        port = parts.port
    except ValueError:
        return None
    scheme = parts.scheme.lower()
    if scheme not in (("https", "http") if allow_http else ("https",)) or not host:
        return None
    if parts.username is not None or parts.password is not None or "@" in parts.netloc:
        return None
    project = ("/" + parts.path.strip("/")).split("/-/", 1)[0].strip("/")
    project = project.removesuffix(".git").strip("/")
    if not project:
        return None
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    return f"{scheme}://{netloc}", project


def _origin(url: str) -> tuple[str, str, int | None]:
    parts = urlsplit(url.strip())
    if "@" in parts.netloc or "\\" in parts.netloc:  # userinfo, or a backslash browsers read as "/"
        raise ValueError("unusable origin")
    scheme = parts.scheme.lower()
    host = (parts.hostname or "").lower()
    port = parts.port
    if port == {"https": 443, "http": 80}.get(scheme):
        port = None
    return scheme, host, port


def same_origin(url_a: str, url_b: str) -> bool:
    """True if both URLs share scheme, host and port (default ports count as no port)."""
    try:
        a, b = _origin(url_a), _origin(url_b)
    except (ValueError, AttributeError):
        return False
    return bool(a[1]) and a == b


def _target(project_url: str, token: str, allow_http: bool) -> tuple[str, str]:
    parsed = parse_project_url(project_url, allow_http=allow_http)
    if parsed is None or not token:
        raise GitLabError("GitLab is not configured correctly")
    base, project = parsed
    return f"{base}/api/v4/projects/{quote(project, safe='')}", token


def _send(method: str, url: str, token: str, **kwargs) -> httpx.Response:
    try:
        with httpx.Client(transport=_transport, timeout=TIMEOUT_SECONDS, follow_redirects=False) as client:
            response = client.request(method, url, headers={"PRIVATE-TOKEN": token}, **kwargs)
    except httpx.HTTPError as exc:
        # Class name only: the message could echo request details.
        raise GitLabError(f"GitLab unreachable ({type(exc).__name__})") from None
    except Exception as exc:  # noqa: BLE001 - httpx/idna/codec errors while building the request
        # Local input problem (e.g. a non-ASCII token); class name only, it could name a character.
        raise GitLabError(f"GitLab request could not be sent ({type(exc).__name__})") from None
    if not 200 <= response.status_code < 300:  # a redirect lands here, too
        raise GitLabError(f"GitLab answered HTTP {response.status_code}")
    return response


def _json_object(response: httpx.Response) -> dict | None:
    try:
        body = response.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def check_project(project_url: str, token: str, *, allow_http: bool = False) -> bool:
    """True if the project can be read with the token. Never raises."""
    try:
        api, token = _target(project_url, token, allow_http)
        _send("GET", api, token)
    except GitLabError:
        return False
    return True


def upload_file(
    project_url: str,
    token: str,
    *,
    filename: str,
    data: bytes,
    content_type: str,
    allow_http: bool = False,
) -> str:
    """Upload a file to the project; returns the Markdown snippet GitLab answers with."""
    api, token = _target(project_url, token, allow_http)
    response = _send("POST", f"{api}/uploads", token, files={"file": (filename, data, content_type)})
    body = _json_object(response)
    markdown = body.get("markdown") if body else None
    if not isinstance(markdown, str) or not markdown:
        raise GitLabError("GitLab upload returned no markdown")
    return markdown


def create_issue(
    project_url: str,
    token: str,
    *,
    title: str,
    description: str,
    confidential: bool = False,
    labels: Sequence[str] = (),
    allow_http: bool = False,
) -> Issue:
    """Create an issue. With ``confidential=True`` the answer must confirm it, else GitLabError.

    ``labels`` must be a sequence of strings; a plain ``str`` raises ``TypeError`` (it would
    otherwise be split into single characters).
    """
    if isinstance(labels, str):
        raise TypeError("labels must be a sequence of strings, not a single string")
    api, token = _target(project_url, token, allow_http)
    fields = {"title": title, "description": description}
    if confidential:
        fields["confidential"] = "true"
    if labels:
        fields["labels"] = ",".join(labels)
    response = _send("POST", f"{api}/issues", token, data=fields)
    body = _json_object(response)
    if confidential and (body is None or body.get("confidential") is not True):
        raise GitLabError("GitLab did not create a confidential issue")
    body = body or {}
    iid = body.get("iid")
    web_url = body.get("web_url")
    if isinstance(web_url, str):
        web_url = web_url.strip()
        try:
            ok = urlsplit(web_url).scheme.lower() in ("http", "https") and same_origin(web_url, project_url)
        except ValueError:
            ok = False
        web_url = web_url if ok else None
    else:
        web_url = None
    return Issue(iid=iid if type(iid) is int and iid >= 1 else None, web_url=web_url)
