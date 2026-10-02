# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""The feature flags a tool's SPA needs at load time.

Every -bar tool mixes the same three keys into its ``/api/whoami/`` payload
(next to ``basicbar_auth.views.whoami_payload``) so the SPA can show or hide
optional features without a second round-trip or build variants::

    return JsonResponse({**whoami_payload(request), **capabilities_payload()})

This replaces the former ``CapabilitiesView`` (``GET /api/capabilities/``),
which no tool ever called — one request at startup is enough.
"""
from django.conf import settings

from . import ai, translation_service


def capabilities_payload() -> dict:
    return {
        # AI-assisted features (LiteLLM proxy) may be offered.
        "ai_enabled": ai.is_enabled(),
        # Canonical authoring language of this deployment (modeltranslation's
        # default), and whether machine-translation drafts are available.
        "content_default_language": getattr(
            settings, "MODELTRANSLATION_DEFAULT_LANGUAGE", settings.LANGUAGE_CODE
        ),
        "content_translation_enabled": translation_service.is_enabled(),
    }
