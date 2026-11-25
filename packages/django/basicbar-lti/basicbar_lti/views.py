# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Generic LTI 1.3 endpoints: OIDC initiation, JWKS, platform management.

The message-launch endpoint itself is tool code — what a launch lands on
(a room, a pool, a course view) is product logic. Tools compose it from the
primitives in :mod:`basicbar_lti.provisioning` and :mod:`.tool_conf`.
"""
import logging
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from pylti1p3.contrib.django import DjangoOIDCLogin
from pylti1p3.exception import LtiException, OIDCException
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from . import dynreg
from .dynreg_http import RegistrationError
from .dynreg_pages import CANCEL_SCRIPT, page
from .middleware import _ORIGIN_RE
from .models import LtiPlatform, LtiRegistrationToken
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


def _register_param(request, key):
    return request.POST.get(key, request.GET.get(key, ""))


def _config_origin(url):
    try:
        parts = urlsplit(url)
    except ValueError:
        return None
    origin = f"{parts.scheme}://{parts.netloc}"
    return origin if _ORIGIN_RE.match(origin) else None


def _register_response(status, title_de, title_en, body, origin, **kw):
    response = HttpResponse(page(title_de, title_en, body, **kw), status=status)
    if origin:
        response["Content-Security-Policy"] = f"frame-ancestors 'self' {origin}"
    return response


def _error_page(status, de, en, origin):
    body = format_html("<p>{}</p><p class=\"en\">{}</p>", de, en)
    return _register_response(status, "Registrierung", "Registration", body, origin)


@csrf_exempt
def lti_register(request):
    """Dynamic Registration endpoint the LMS admin's browser opens.

    Parameter parsing, branching and page rendering only; the registration
    itself lives in :mod:`basicbar_lti.dynreg`.
    """
    raw = _register_param(request, "token")
    config_url = _register_param(request, "openid_configuration")
    registration_token = _register_param(request, "registration_token")
    confirm = bool(_register_param(request, "confirm"))

    token = LtiRegistrationToken.find_valid(raw)
    if token is None:
        return _error_page(
            403,
            "Link ungültig, bereits verwendet oder abgelaufen — "
            "neuen Link beim Tool-Admin anfordern.",
            "Link invalid, already used or expired — request a new link "
            "from the tool admin.",
            None,
        )
    origin = _config_origin(config_url)
    if not config_url:
        return _error_page(
            400,
            "Diese Adresse in Moodle als Tool-URL eintragen "
            "(Externe Tools → Tools verwalten).",
            "Enter this address in Moodle as the tool URL "
            "(External tools → Manage tools).",
            origin,
        )

    try:
        config = dynreg.load_platform_config(config_url, registration_token)
        if dynreg.known_issuer(config) and not confirm:
            return _confirm_page(raw, config_url, registration_token, origin)
        platform = dynreg.register_platform(request, token, config, registration_token)
    except RegistrationError as exc:
        logger.warning(
            "LTI registration failed (config=%r): %s %s", config_url, exc, exc.detail
        )
        return _error_page(400, str(exc), "Registration failed.", origin)

    body = format_html(
        "<p>Registrierung abgeschlossen ({}). Nächste Schritte in Moodle: "
        "Tool aktivieren; Tool bearbeiten → Standard-Startcontainer "
        "„Neues Fenster“.</p>"
        "<p class=\"en\">Registration complete. Next steps in Moodle: "
        "activate the tool; edit the tool → default launch container "
        "“New window”.</p>",
        platform.name,
    )
    if not platform.deployment_ids:
        body += mark_safe(  # noqa: S308 — static text, no dynamic values
            "<p>Das LMS hat keine Deployment-ID geliefert — im Tool-Admin "
            "nachtragen.</p>"
            "<p class=\"en\">The LMS did not provide a deployment ID — add "
            "it in the tool admin.</p>"
        )
    return _register_response(
        200, "Registrierung abgeschlossen", "Registration complete", body,
        origin, close=True,
    )


def _confirm_page(raw, config_url, registration_token, origin):
    body = format_html(
        "<p>Für {} gibt es bereits eine aktive Verknüpfung. Eine neue "
        "Registrierung legt eine zweite an; die bestehende Verknüpfung wird "
        "nicht übernommen (Kursverknüpfungen und Konten hängen an der "
        "alten).</p>"
        "<p class=\"en\">An active registration already exists for this "
        "platform. A new registration creates a second one; the existing "
        "registration is not taken over (course links and accounts stay "
        "attached to the old one).</p>"
        "<form method=\"post\">"
        "<input type=\"hidden\" name=\"token\" value=\"{}\">"
        "<input type=\"hidden\" name=\"openid_configuration\" value=\"{}\">"
        "<input type=\"hidden\" name=\"registration_token\" value=\"{}\">"
        "<input type=\"hidden\" name=\"confirm\" value=\"1\">"
        "<button type=\"submit\">Trotzdem neu registrieren / Register anyway"
        "</button>"
        "<button type=\"button\" id=\"cancel\">Abbrechen / Cancel</button>"
        "</form>{}",
        _origin_label(config_url),
        raw,
        config_url,
        registration_token,
        CANCEL_SCRIPT,
    )
    return _register_response(
        200, "Registrierung bestätigen", "Confirm registration", body, origin
    )


def _origin_label(config_url):
    try:
        return urlsplit(config_url).netloc or config_url
    except ValueError:
        return config_url
