# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Sealed-off HTTP client for the two outbound requests of Dynamic
Registration (fetch the platform's OpenID configuration, POST the tool
registration).

The URLs come from an LMS admin's browser, so they are untrusted: only
https (unless ``LTI_REGISTRATION_ALLOW_HTTP``), no loopback / link-local /
unspecified target addresses, same-origin redirects only, bounded time and
size, JSON objects only. Private networks stay allowed (on-prem Moodle).
"""

import http.client
import ipaddress
import json
import socket
import urllib.error
import urllib.request
from urllib.parse import urlsplit

from . import conf

TIMEOUT = 10  # seconds
MAX_BYTES = 256 * 1024
_DETAIL_CHARS = 500


class RegistrationError(Exception):
    """``str(exc)`` is the (German) message for the platform admin;
    ``detail`` is for the log only."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


def _origin(url: str) -> tuple[str, str, int | None]:
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise RegistrationError(
            "Die Adresse ist ungültig.", detail=url
        ) from exc
    try:
        port = parts.port
    except ValueError:
        port = None
    return (parts.scheme.lower(), (parts.hostname or "").lower(), port)


def _default_port(scheme: str) -> int:
    return 443 if scheme == "https" else 80


class _SameOriginRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        old, new = _origin(req.full_url), _origin(newurl)
        if (old[0], old[1], old[2] or _default_port(old[0])) != (
            new[0],
            new[1],
            new[2] or _default_port(new[0]),
        ):
            raise RegistrationError(
                "Die Plattform leitet auf eine andere Adresse um; das wird "
                "aus Sicherheitsgründen abgelehnt.",
                detail=f"redirect {req.full_url} -> {newurl}",
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


_opener = urllib.request.build_opener(_SameOriginRedirectHandler)


def _open(req: urllib.request.Request):
    """The single I/O seam (patched in tests)."""
    return _opener.open(req, timeout=TIMEOUT)


def _check_address(host: str, port: int) -> None:
    try:
        infos = socket.getaddrinfo(host, port)
    except (socket.gaierror, UnicodeError, OSError) as exc:
        raise RegistrationError(
            "Die Adresse der Plattform konnte nicht aufgelöst werden.",
            detail=f"{host}: {exc}",
        ) from exc
    if not infos:
        raise RegistrationError(
            "Die Adresse der Plattform konnte nicht aufgelöst werden.",
            detail=host,
        )
    for info in infos:
        raw = str(info[4][0]).split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(raw)
        except ValueError as exc:
            raise RegistrationError(
                "Die Adresse der Plattform ist ungültig.", detail=raw
            ) from exc
        if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
            ip = ip.ipv4_mapped
        if ip.is_loopback or ip.is_link_local or ip.is_unspecified:
            raise RegistrationError(
                "Die Adresse der Plattform zeigt auf einen nicht erlaubten "
                "Bereich (lokal, link-lokal oder unspezifiziert).",
                detail=f"{host} -> {raw}",
            )


def request_json(
    url: str, *, bearer: str | None = None, payload: dict | None = None
) -> dict:
    """GET ``url`` (POST JSON when ``payload`` is given); return the JSON
    object of the answer or raise :class:`RegistrationError`."""
    allow_http = bool(conf.get("LTI_REGISTRATION_ALLOW_HTTP"))
    scheme, host, port = _origin(url)
    if scheme != "https" and not (allow_http and scheme == "http"):
        raise RegistrationError(
            "Die Adresse muss mit https:// beginnen.", detail=url
        )
    if not host:
        raise RegistrationError("Die Adresse ist ungültig.", detail=url)
    try:
        parts = urlsplit(url)
        parts.port  # noqa: B018 - raises ValueError on a bad port
    except ValueError as exc:
        raise RegistrationError(
            "Die Adresse ist ungültig.", detail=url
        ) from exc
    if parts.username is not None or parts.password is not None:
        raise RegistrationError(
            "Die Adresse darf keine Zugangsdaten enthalten.", detail=url
        )
    if not allow_http:
        _check_address(host, port or _default_port(scheme))

    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    req = urllib.request.Request(
        url, data=data, headers=headers, method="POST" if data else "GET"
    )

    try:
        with _open(req) as resp:
            body = resp.read(MAX_BYTES + 1)
    except RegistrationError:
        raise
    except urllib.error.HTTPError as exc:
        try:
            excerpt = exc.read(_DETAIL_CHARS * 4).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 - detail is best effort
            excerpt = ""
        raise RegistrationError(
            f"Die Plattform hat die Anfrage abgelehnt (HTTP {exc.code}).",
            detail=f"{exc.code} {url}: {excerpt[:_DETAIL_CHARS]}",
        ) from exc
    except (
        urllib.error.URLError,
        http.client.HTTPException,
        OSError,
        ValueError,
    ) as exc:
        raise RegistrationError(
            "Die Plattform ist nicht erreichbar.", detail=f"{url}: {exc}"
        ) from exc

    if len(body) > MAX_BYTES:
        raise RegistrationError(
            "Die Antwort der Plattform ist zu groß.", detail=url
        )
    try:
        result = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise RegistrationError(
            "Die Plattform hat keine gültige JSON-Antwort geliefert.",
            detail=body[:_DETAIL_CHARS].decode("utf-8", "replace"),
        ) from exc
    if not isinstance(result, dict):
        raise RegistrationError(
            "Die Plattform hat keine gültige JSON-Antwort geliefert.",
            detail=body[:_DETAIL_CHARS].decode("utf-8", "replace"),
        )
    return result
