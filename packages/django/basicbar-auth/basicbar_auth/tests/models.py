# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.db import models

from basicbar_auth.models import AbstractBasicUser


class TestUser(AbstractBasicUser):
    """Concrete user for the package test suite — shaped like a tool with the
    retention convention, so the MAX_USERS slot-counting is exercised too."""

    anonymized_at = models.DateTimeField(null=True, blank=True)
