# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Settings access with package defaults.

Every setting defaults to "off"/empty, so a project that installs the app
without configuring anything behaves exactly as before — features stay
invisible until the deployment opts in via environment settings.
"""

from django.conf import settings

DEFAULTS = {
    # LiteLLM (OpenAI-compatible endpoint)
    "AI_PROVIDER": "none",  # "none" | "litellm"
    "AI_BASE_URL": "",  # e.g. https://litellm.example.org/v1
    "AI_API_KEY": "",
    "AI_MODEL": "",
    "AI_TIMEOUT": 30,
    "AI_MAX_TOKENS": 2000,
    "AI_DISABLE_THINKING": True,
    # LibreTranslate
    "CONTENT_TRANSLATION_PROVIDER": "none",  # "none" | "libretranslate"
    "LIBRETRANSLATE_URL": "",
    "LIBRETRANSLATE_API_KEY": "",
}


def get(name: str):
    """Return the project's setting, or the package default when unset."""
    return getattr(settings, name, DEFAULTS[name])
