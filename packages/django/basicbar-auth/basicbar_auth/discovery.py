# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Resolve OIDC endpoints from a provider's discovery document.

Used so that, in production, setting a single ``OIDC_OP_ISSUER`` is enough to
talk to any compliant OIDC provider — no per-endpoint configuration needed.
"""
import json
import urllib.request


def discover_endpoints(issuer, timeout=5):
    """Fetch ``{issuer}/.well-known/openid-configuration``.

    Returns the parsed document, or an empty dict on any failure (so settings
    import never crashes if the provider is temporarily unreachable).
    """
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return json.load(response)
    except Exception:
        return {}
