# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Resolve OIDC endpoints from a provider's discovery document.

Used so that, in production, setting a single ``OIDC_OP_ISSUER`` is enough to
talk to any compliant OIDC provider — no per-endpoint configuration needed.
"""
import json
import logging
import urllib.request

logger = logging.getLogger(__name__)


def discover_endpoints(issuer, timeout=5):
    """Fetch ``{issuer}/.well-known/openid-configuration``.

    Returns the parsed document, or an empty dict on any failure, so a
    settings import never crashes because the provider is temporarily
    unreachable — the failure is logged, and the settings should refuse to
    start without ``DEBUG`` when the endpoints end up empty (the template
    does), otherwise every login fails with an opaque error later.
    """
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            document = json.load(response)
    except Exception as exc:  # noqa: BLE001 — network, HTTP, JSON: all "no document"
        logger.warning("OIDC discovery failed for %s: %s", url, exc)
        return {}
    if not isinstance(document, dict):
        logger.warning("OIDC discovery for %s returned no JSON object", url)
        return {}
    return document
