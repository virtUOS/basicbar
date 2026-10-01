# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Shared bits for the stdlib-``urllib`` provider clients."""

from http.client import HTTPException
from urllib import error

# Everything a ``urlopen`` + ``read`` + ``json.loads`` round trip can raise.
# ``URLError``/``HTTPError``/``TimeoutError``/``ConnectionResetError`` are all
# ``OSError`` subclasses; ``IncompleteRead``/``RemoteDisconnected`` are
# ``HTTPException``; the rest covers a malformed or unexpectedly shaped body.
TRANSPORT_ERRORS = (OSError, HTTPException, ValueError, KeyError, IndexError, TypeError)

_MAX_DETAIL = 300


def http_error_detail(exc: error.HTTPError) -> str:
    """The first bytes of an HTTP error body — providers put the actual cause
    there (``{"error": "en is not supported"}``), ``str(exc)`` only says
    ``HTTP Error 400: Bad Request``."""
    try:
        body = exc.read(_MAX_DETAIL + 1)
    except Exception:  # noqa: BLE001 — a body that can't be read adds nothing
        return ""
    text = body.decode("utf-8", errors="replace").strip()
    if len(text) > _MAX_DETAIL:
        text = text[:_MAX_DETAIL] + "…"
    return text
