# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Keep the user → session index (``UserSession``) in sync with Django's
login/logout. Connected in ``apps.py``; both handlers are best-effort so a
hiccup in the index can never break a login."""
import logging

from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from .models import UserSession

logger = logging.getLogger(__name__)


@receiver(user_logged_in, dispatch_uid="basicbar_auth.record_session")
def record_session(sender, request, user, **kwargs):
    # ``login()`` has already cycled the key, so this is the key the browser
    # will carry from now on.
    key = getattr(getattr(request, "session", None), "session_key", None)
    if not key:
        return
    try:
        UserSession.objects.update_or_create(session_key=key, defaults={"user": user})
    except Exception:  # noqa: BLE001 — index maintenance must never break login
        logger.exception("Could not record session for user %s", user.pk)


@receiver(user_logged_out, dispatch_uid="basicbar_auth.forget_session")
def forget_session(sender, request, user, **kwargs):
    # Sent before ``logout()`` flushes the session, so the key is still there.
    key = getattr(getattr(request, "session", None), "session_key", None)
    if not key:
        return
    try:
        UserSession.objects.filter(session_key=key).delete()
    except Exception:  # noqa: BLE001
        logger.exception("Could not forget session %s", key[:8])
