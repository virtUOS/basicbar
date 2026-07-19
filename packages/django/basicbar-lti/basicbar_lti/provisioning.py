# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Launch-data helpers: roles, platform matching, JIT user provisioning.

The user model must provide the ``subject``/``claims`` fields of
``basicbar_auth.models.AbstractBasicUser`` (or equivalents).
"""
import logging

from django.contrib.auth import get_user_model
from pylti1p3.contrib.django import DjangoCacheDataStorage

from .models import LtiPlatform, LtiUserLink

logger = logging.getLogger(__name__)

CLAIM = "https://purl.imsglobal.org/spec/lti/claim/"
INSTRUCTOR_ROLE_MARKERS = ("membership#Instructor", "membership#Administrator",
                           "institution/person#Administrator")


def launch_storage():
    return DjangoCacheDataStorage(cache_name="default")


def is_instructor(launch_data):
    roles = launch_data.get(f"{CLAIM}roles") or []
    return any(marker in role for role in roles for marker in INSTRUCTOR_ROLE_MARKERS)


def platform_for(launch_data):
    issuer = launch_data.get("iss", "")
    audience = launch_data.get("aud")
    client_id = audience[0] if isinstance(audience, list) else audience
    return LtiPlatform.objects.filter(
        issuer=issuer, client_id=client_id, is_active=True
    ).first()


def provision_user(platform, launch_data):
    """JIT user for LTI instructors — one local user per person.

    Resolution order: (1) the stored ``LtiUserLink`` for this platform
    subject, (2) legacy users created before the link table existed,
    (3) with the platform's ``link_by_email`` opt-in, the existing (OIDC)
    user with the same e-mail — only on an unambiguous match, (4) a new
    LTI-native user. The resolved user is recorded in the link table, so
    steps 2–4 run at most once per subject.
    """
    sub = launch_data["sub"]
    link = (
        LtiUserLink.objects.filter(platform=platform, sub=sub)
        .select_related("user")
        .first()
    )
    if link is not None:
        user = link.user
    else:
        subject = f"lti:{platform.pk}:{sub}"
        user_model = get_user_model()
        user = user_model.objects.filter(subject=subject).first()
        email = (launch_data.get("email") or "").strip()
        if user is None and platform.link_by_email and email:
            matches = list(user_model.objects.filter(email__iexact=email)[:2])
            if len(matches) == 1:
                user = matches[0]
                logger.info(
                    "LTI launch linked to existing user #%s by e-mail "
                    "(platform %s)", user.pk, platform.pk,
                )
        if user is None:
            user = user_model(
                username=f"lti-{platform.pk}-{sub}"[:150], subject=subject
            )
        _update_lti_profile(user, launch_data)
        LtiUserLink.objects.create(platform=platform, sub=sub, user=user)
        return user

    _update_lti_profile(user, launch_data)
    return user


def _update_lti_profile(user, launch_data):
    """Refresh profile fields from the launch — but only for LTI-native
    users. For accounts linked to an OIDC identity, the IdP stays the
    source of truth (the launch must not clobber name, e-mail or the
    claims used for the admin-group sync)."""
    if user.pk is not None and not (user.subject or "").startswith("lti:"):
        return
    user.email = launch_data.get("email", user.email or "")
    user.first_name = launch_data.get("given_name", user.first_name or "")
    user.last_name = launch_data.get("family_name", user.last_name or "")
    user.claims = {k: v for k, v in launch_data.items() if isinstance(k, str)}
    user.save()
