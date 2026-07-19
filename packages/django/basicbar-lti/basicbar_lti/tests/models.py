# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.contrib.auth.models import AbstractUser
from django.db import models


class TestUser(AbstractUser):
    """Minimal user with the ``subject``/``claims`` fields the provisioning
    relies on (shape of ``basicbar_auth.models.AbstractBasicUser``)."""

    subject = models.CharField(max_length=255, unique=True, null=True, blank=True)
    claims = models.JSONField(default=dict, blank=True)
