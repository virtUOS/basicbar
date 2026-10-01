# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.apps import AppConfig


class BasicbarAuthConfig(AppConfig):
    name = "basicbar_auth"
    verbose_name = "Basicbar Auth"
    # Pinned here so the package's own migration is the same in every tool,
    # whatever the project's DEFAULT_AUTO_FIELD.
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from . import signals  # noqa: F401 — connects the session-index receivers
