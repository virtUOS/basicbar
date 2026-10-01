# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Generic LTI 1.3 endpoints: OIDC initiation, JWKS, platform management.

The message-launch endpoint itself is tool code — what a launch lands on
(a room, a pool, a course view) is product logic. Tools compose it from the
primitives in :mod:`basicbar_lti.provisioning` and :mod:`.tool_conf`.
"""
import logging

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pylti1p3.contrib.django import DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LtiPlatform
from .provisioning import launch_storage
from .serializers import LtiPlatformSerializer
from .tool_conf import build_tool_conf

logger = logging.getLogger(__name__)


def _login_param(request, key):
    """A login-init param, from POST first then the query string."""
    return request.POST.get(key, request.GET.get(key, ""))


def _find_registration(tool_conf, iss, client_id):
    """Resolve the platform registration, or None if nothing matches.

    pylti1p3 raises a bare ``Exception`` deep inside ``redirect()`` when the
    issuer / client_id doesn't map to a registration (e.g. a trailing-slash
    mismatch, or a client_id the LMS sends that we never registered). We
    resolve it up front — with the same one-client/many-clients branching the
    library uses internally — so an operator gets an actionable 400 instead of
    an opaque 500.
    """
    try:
        if tool_conf.check_iss_has_one_client(iss):
            return tool_conf.find_registration_by_issuer(iss)
        return tool_conf.find_registration_by_params(iss, client_id)
    except Exception:  # noqa: BLE001 — get_iss_config raises a plain Exception
        return None


@csrf_exempt
def lti_login(request):
    """OIDC third-party initiated login (the platform POSTs/GETs here).

    Missing parameters and unresolvable registrations answer with a clear
    ``400`` (and a logged issuer/client_id) rather than crashing with a
    generic ``500`` — LTI misconfigurations are the common case here and the
    platform operator needs to see what was actually received.
    """
    target = _login_param(request, "target_link_uri")
    if not target:
        return _bad_request("Missing target_link_uri")

    iss = _login_param(request, "iss")
    login_hint = _login_param(request, "login_hint")
    client_id = _login_param(request, "client_id")
    if not iss:
        return _bad_request("Missing iss")
    if not login_hint:
        return _bad_request("Missing login_hint")

    tool_conf = build_tool_conf()
    if _find_registration(tool_conf, iss, client_id) is None:
        logger.warning(
            "LTI login: no platform registered for issuer=%r client_id=%r",
            iss, client_id,
        )
        return _bad_request(
            f"No LTI platform registered for issuer={iss!r} "
            f"client_id={client_id!r}. Check the platform registration "
            f"(issuer and client_id must match exactly, including any "
            f"trailing slash)."
        )

    try:
        oidc_login = DjangoOIDCLogin(
            request, tool_conf, launch_data_storage=launch_storage()
        )
        return oidc_login.redirect(target)
    except (OIDCException, LtiException) as exc:
        logger.warning(
            "LTI login init failed (issuer=%r client_id=%r): %s",
            iss, client_id, exc,
        )
        return _bad_request(f"LTI login failed: {exc}")


def _bad_request(message):
    """A 400 that echoes request parameters for the operator — as plain text,
    never HTML: the endpoint is reachable via GET, so an HTML body would be a
    reflected-XSS vector on the tool's origin."""
    return HttpResponse(message, status=400, content_type="text/plain; charset=utf-8")


def lti_jwks(request):
    """The tool's public key set (register this URL in the platform)."""
    return JsonResponse(build_tool_conf().get_jwks(), safe=False)


class LtiPlatformViewSet(viewsets.ModelViewSet):
    """Staff-only CRUD for LTI platform registrations (web admin).

    Subclass to change the permission (default: Django staff)."""

    queryset = LtiPlatform.objects.all().order_by("name")
    serializer_class = LtiPlatformSerializer
    permission_classes = [IsAdminUser]


class LtiToolInfoView(APIView):
    """The tool's own LTI endpoints, for pasting into the LMS registration.

    Assumes the conventional ``/lti/…`` paths under ``FRONTEND_BASE_URL``."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        base = settings.FRONTEND_BASE_URL.rstrip("/")
        return Response({
            "login_url": f"{base}/lti/login/",
            "launch_url": f"{base}/lti/launch/",
            "jwks_url": f"{base}/lti/jwks/",
            "icon_url": f"{base}/lti/icon.svg",
        })
