# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Settings access with package defaults."""

from datetime import timedelta

from django.conf import settings

DEFAULTS = {
    # HTML paths that may be embedded by registered LMS platforms (the
    # frame-ancestors middleware acts only under these prefixes). Tools add
    # their embeddable surfaces, e.g. abstimmbar: ("/lti/", "/p/").
    "LTI_FRAME_PATH_PREFIXES": ("/lti/",),
    # Dynamic Registration: lifetime of a one-time registration token.
    "LTI_REGISTRATION_TOKEN_TTL": timedelta(days=7),
    # Allow http:// and loopback/link-local targets (local development only).
    "LTI_REGISTRATION_ALLOW_HTTP": False,
    # What the tool announces to the platform; the project's setting is
    # merged flat (key by key) over this dict.
    "LTI_TOOL_REGISTRATION": {
        "client_name": "LTI Tool",
        "description": "",
        "logo_path": "",
        "messages": [{"type": "LtiResourceLinkRequest"}],
        "claims": ["iss", "sub", "name", "given_name", "family_name", "email"],
        "scope": "",
        "custom_parameters": {},
    },
}


def get(name: str):
    """Return the project's setting, or the package default when unset."""
    return getattr(settings, name, DEFAULTS[name])


def tool_registration() -> dict:
    """Default tool registration, overridden key by key by the project."""
    return {**DEFAULTS["LTI_TOOL_REGISTRATION"], **get("LTI_TOOL_REGISTRATION")}
