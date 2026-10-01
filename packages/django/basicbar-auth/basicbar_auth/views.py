# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Session/identity endpoints for a tool's SPA.

Plain Django views (no DRF): the SPA calls them with the session cookie and
the CSRF token it got from ``whoami``. A tool with extra fields in its
``whoami`` composes ``whoami_payload`` into its own view — see the README.
"""
import json

from django.conf import settings
from django.contrib.auth import logout as django_logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

from .oidc import provider_logout_url


def whoami_payload(request) -> dict:
    """The session state the SPA needs at load time.

    Always includes the CSRF token: ``get_token`` sets the cookie *and* hands
    the SPA an authoritative token, so unsafe requests work even cross-origin
    in dev, where reading the cookie from JavaScript can be unreliable
    (production is same-origin behind the reverse proxy).
    """
    payload = {"authenticated": False, "csrf_token": get_token(request)}
    user = request.user
    if not user.is_authenticated:
        return payload
    payload.update(
        {
            "authenticated": True,
            "username": user.get_username(),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "subject": getattr(user, "subject", None),
            "is_staff": user.is_staff,
            "language": getattr(user, "language", ""),
        }
    )
    return payload


def whoami(request):
    """``GET /api/whoami/`` — the plain payload; tools with extra fields wrap
    ``whoami_payload`` instead of using this view."""
    return JsonResponse(whoami_payload(request))


def logout_view(request):
    """Log out of Django and (if logged in via OIDC) the identity provider.

    GET-friendly so the SPA can trigger it with a plain redirect.
    """
    end_session_url = None
    if request.user.is_authenticated and getattr(settings, "OIDC_OP_LOGOUT_ENDPOINT", ""):
        end_session_url = provider_logout_url(request)
    django_logout(request)
    return redirect(end_session_url or settings.LOGOUT_REDIRECT_URL)


@require_POST
def set_language(request):
    """``POST /api/whoami/language/`` ``{"language": "de"}`` — remember the
    user's UI language (``AbstractBasicUser.language``). Accepts only codes
    from ``settings.LANGUAGES``."""
    if not request.user.is_authenticated:
        return JsonResponse({"detail": "Not authenticated."}, status=403)
    try:
        data = json.loads(request.body or b"{}")
    except ValueError:
        data = {}
    raw = data.get("language") if isinstance(data, dict) else ""
    language = (str(raw) if raw else "").strip()
    if language not in dict(settings.LANGUAGES):
        return JsonResponse({"detail": "Unsupported language."}, status=400)
    request.user.language = language
    request.user.save(update_fields=["language"])
    return JsonResponse({"language": language})
