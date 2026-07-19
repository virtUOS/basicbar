# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""User accounts, provisioned just-in-time on first OIDC login.

The OIDC machinery lives in basicbar-auth; this concrete model carries the
tool's own fields (basicbar ADR-0003). Add tool-specific fields here with
normal migrations.
"""
from basicbar_auth.models import AbstractBasicUser
from django.db import models


class User(AbstractBasicUser):
    """Application user (``subject``/``claims`` come from AbstractBasicUser)."""

    # Preferred UI language ("en"/"de"), set from the SPA; blank = site default.
    language = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.get_username()
