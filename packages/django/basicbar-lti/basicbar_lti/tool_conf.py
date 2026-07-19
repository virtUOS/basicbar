# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Bridge from the DB registrations to pylti1p3's ToolConfDict."""
from pylti1p3.tool_config import ToolConfDict

from .models import LtiPlatform, LtiToolKey


def build_tool_conf():
    """ToolConfDict over all active platform registrations."""
    key = LtiToolKey.load()
    settings = {}
    platforms = list(LtiPlatform.objects.filter(is_active=True))
    for platform in platforms:
        settings.setdefault(platform.issuer, []).append(
            {
                "client_id": platform.client_id,
                "auth_login_url": platform.auth_login_url,
                "auth_token_url": platform.auth_token_url,
                "auth_audience": None,
                "key_set_url": platform.key_set_url or None,
                "key_set": platform.key_set,
                "deployment_ids": list(platform.deployment_ids or []),
            }
        )
    tool_conf = ToolConfDict(settings)
    for platform in platforms:
        tool_conf.set_private_key(
            platform.issuer, key.private_key, client_id=platform.client_id
        )
        tool_conf.set_public_key(
            platform.issuer, key.public_key, client_id=platform.client_id
        )
    return tool_conf
