# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Settings access with package defaults.

Claim names and the admin-group mapping are configuration, so switching
identity providers needs no code changes. Everything optional defaults to
"off"; the mozilla-django-oidc client settings (OIDC_RP_*, OIDC_OP_*) stay
plain Django settings as that library expects them.
"""

from django.conf import settings

DEFAULTS = {
    # Which OIDC claims map onto the user record.
    "OIDC_CLAIM_USERNAME": "preferred_username",
    "OIDC_CLAIM_EMAIL": "email",
    "OIDC_CLAIM_FIRST_NAME": "given_name",
    "OIDC_CLAIM_LAST_NAME": "family_name",
    # IdP group that grants Django admin (empty = no group mapping).
    "OIDC_GROUPS_CLAIM": "groups",
    "OIDC_ADMIN_GROUP": "",
    # Issuer used to validate back-channel logout tokens (empty = skip check).
    "OIDC_OP_ISSUER": "",
    # Back-channel logout tokens older than this (seconds, measured from
    # ``iat``) are rejected as replays; also absorbs clock skew.
    "OIDC_BACKCHANNEL_MAX_AGE": 300,
    # Opt-in: when the IdP re-issued its subjects (re-imported dev realm,
    # realm/IdP migration), fall back to a username match instead of crashing
    # into the unique-username constraint. Only enable when the IdP never
    # re-assigns usernames to different people — see the README's operator
    # notes on username vacancy.
    "OIDC_MATCH_BY_USERNAME_FALLBACK": False,
    # Optional per-deployment cap on accounts (None = unlimited).
    "MAX_USERS": None,
}


def get(name: str):
    """Return the project's setting, or the package default when unset."""
    return getattr(settings, name, DEFAULTS[name])
