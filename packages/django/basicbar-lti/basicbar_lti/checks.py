# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""System checks for the Dynamic Registration settings."""
from django.conf import settings
from django.core.checks import Warning, register

from . import conf


@register()
def check_registration_settings(app_configs, **kwargs):
    if conf.get("LTI_REGISTRATION_ALLOW_HTTP") and not settings.DEBUG:
        return [
            Warning(
                "LTI_REGISTRATION_ALLOW_HTTP is enabled while DEBUG is off.",
                hint=(
                    "LTI_REGISTRATION_ALLOW_HTTP allows http:// and "
                    "loopback/link-local targets for Dynamic Registration; "
                    "use it for local development only."
                ),
                id="basicbar_lti.W001",
            )
        ]
    return []
