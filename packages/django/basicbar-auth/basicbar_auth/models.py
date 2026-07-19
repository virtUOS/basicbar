# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.contrib.auth.models import AbstractUser
from django.db import models


class AbstractBasicUser(AbstractUser):
    """Base for the tools' user models: Django's ``AbstractUser`` plus the two
    fields the shared OIDC machinery relies on.

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

    class Meta(AbstractUser.Meta):
        abstract = True
