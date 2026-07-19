# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Allow the registered LMS platforms to embed the tool in an iframe.

Django's XFrameOptionsMiddleware sends ``X-Frame-Options: DENY`` on every
response, which blocks any iframe embedding — including a legitimate LTI
launch shown inside the LMS. For HTML responses under the configured iframe
surfaces (``LTI_FRAME_PATH_PREFIXES``, default ``/lti/``) we replace that
header with a CSP ``frame-ancestors`` directive that allows only ``'self'``
plus the scheme+host origins of the *active* registered LTI platforms (no
wildcard); origins are validated against a strict ``scheme://host[:port]``
pattern so a malformed ``issuer`` value cannot inject extra tokens into the
header. All other responses (API/SSE, and any HTML outside those path
prefixes — e.g. the Django admin) are left untouched. Place it ABOVE
XFrameOptionsMiddleware so it runs after it on the response and its header
wins.
"""
import re
from urllib.parse import urlsplit

from . import conf

# scheme://host[:port], nothing else — rejects any stray whitespace or
# separator characters (e.g. ";", " ") that a garbled/crafted issuer value
# could otherwise smuggle into the Content-Security-Policy header.
_ORIGIN_RE = re.compile(r"^https?://[A-Za-z0-9.-]+(:[0-9]+)?$")


def _lms_origins():
    from .models import LtiPlatform

    origins = []
    for issuer in (
        LtiPlatform.objects.filter(is_active=True).values_list("issuer", flat=True)
    ):
        parts = urlsplit((issuer or "").strip())
        origin = f"{parts.scheme}://{parts.netloc}"
        if parts.scheme in ("http", "https") and _ORIGIN_RE.match(origin):
            origins.append(origin)
    # de-duplicate, stable order
    seen, unique = set(), []
    for o in origins:
        if o not in seen:
            seen.add(o)
            unique.append(o)
    return unique


class LtiFrameAncestorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        ct = response.get("Content-Type", "")
        prefixes = tuple(conf.get("LTI_FRAME_PATH_PREFIXES"))
        if ct.startswith("text/html") and request.path.startswith(prefixes):
            ancestors = " ".join(["'self'", *_lms_origins()])
            response["Content-Security-Policy"] = f"frame-ancestors {ancestors}"
            response.headers.pop("X-Frame-Options", None)
        return response
