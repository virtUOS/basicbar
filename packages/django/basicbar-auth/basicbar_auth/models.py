# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class AbstractBasicUser(AbstractUser):
    """Base for the tools' user models: Django's ``AbstractUser`` plus the
    fields the shared OIDC machinery and session endpoints rely on.

    Each tool defines its own concrete ``accounts.User(AbstractBasicUser)``
    with its own fields and migrations (see basicbar ADR-0003) — tool-specific
    data like strikes, retention timestamps or editor preferences never lives
    here.
    """

    # OIDC subject identifier (stable, unique per identity provider).
    subject = models.CharField(max_length=255, unique=True, null=True, blank=True)

    # Snapshot of the OIDC claims from the last login; basis for group
    # mappings and claim-based access rules.
    claims = models.JSONField(default=dict, blank=True)

    # Preferred UI (and e-mail) language, set from the SPA via
    # ``basicbar_auth.views.set_language``; blank = site default.
    language = models.CharField(max_length=10, blank=True)

    class Meta(AbstractUser.Meta):
        abstract = True


class UserSession(models.Model):
    """Index from user to live Django session, maintained by the
    ``user_logged_in`` / ``user_logged_out`` signals (see ``signals.py``).

    Django's DB session store has no such index — the only way to find a
    user's sessions is to decode every unexpired session row. The back-channel
    logout needs exactly that lookup, and a tool with many anonymous visitor
    sessions (participants, public catalogue) would pay for all of them on
    every SSO logout. Rows are dropped when the user logs out, when the
    back-channel logout acts on them, and — for sessions that expired
    silently — lazily on the next lookup for that user.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="basicbar_sessions",
    )
    session_key = models.CharField(max_length=40)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Package-prefixed name: Postgres constraint names are schema-wide.
            models.UniqueConstraint(
                fields=["session_key"], name="basicbar_auth_usersession_key_uniq"
            ),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.session_key[:8]}…"
