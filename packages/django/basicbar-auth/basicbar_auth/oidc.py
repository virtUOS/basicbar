# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""OIDC integration for the tools' custom user models.

Provider-agnostic: claim names and the admin-group mapping come from settings,
so switching identity providers needs configuration, not code changes. The
optional behaviours — account cap (``MAX_USERS``) and the subject-drift
username fallback (``OIDC_MATCH_BY_USERNAME_FALLBACK``) — are off unless the
deployment opts in; see the README's operator notes.
"""
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.views import OIDCAuthenticationRequestView

from . import conf

logger = logging.getLogger(__name__)

# The event a valid OIDC back-channel logout token must carry (OpenID Connect
# Back-Channel Logout 1.0, §2.4).
BACKCHANNEL_LOGOUT_EVENT = "http://schemas.openid.net/event/backchannel-logout"


def claims_in_admin_group(claims) -> bool:
    """Whether the given OIDC ``claims`` place the user in the configured admin
    group. Returns ``False`` when no ``OIDC_ADMIN_GROUP`` is set."""
    admin_group = conf.get("OIDC_ADMIN_GROUP")
    if not admin_group:
        return False
    groups = (claims or {}).get(conf.get("OIDC_GROUPS_CLAIM")) or []
    if isinstance(groups, str):
        groups = [groups]
    # Keycloak's Group Membership mapper may send full paths depending on its
    # "Full group path" setting. Match the configured group against the raw
    # value, the leading-slash-stripped value, and the last path segment.
    wanted = admin_group.strip("/")
    return any(
        isinstance(g, str)
        and wanted in {g, g.strip("/"), g.strip("/").split("/")[-1]}
        for g in groups
    )


def is_oidc_admin(user) -> bool:
    """Whether this user's admin rights come from the IdP admin group (as
    opposed to a local promotion). Such rights are managed by the IdP and must
    not be revoked from within the app — the group is authoritative and would
    re-grant them on the next login anyway."""
    return bool(getattr(user, "subject", "")) and claims_in_admin_group(user.claims)


class SilentLoginView(OIDCAuthenticationRequestView):
    """Start an OIDC login with ``prompt=none`` (silent SSO).

    If the IdP already has a session for the visitor, it returns a code and the
    normal callback logs them in. Otherwise it returns ``error=login_required``,
    which mozilla-django-oidc's callback turns into a redirect to
    ``LOGIN_REDIRECT_URL_FAILURE`` (the SPA landing with ``?sso=failed``) — no
    interactive prompt, no loop.
    """

    def get_extra_params(self, request):
        params = super().get_extra_params(request)
        params["prompt"] = "none"
        return params


def _users_counting_toward_cap(UserModel):
    """Accounts that occupy a ``MAX_USERS`` slot. Anonymized (deleted) users
    don't count — removing one frees a slot — recognised by the retention
    convention of an ``anonymized_at`` field; tools without a retention
    feature simply count every account."""
    try:
        UserModel._meta.get_field("anonymized_at")
    except FieldDoesNotExist:
        return UserModel.objects.all()
    return UserModel.objects.filter(anonymized_at__isnull=True)


class OIDCBackend(OIDCAuthenticationBackend):
    """Map OIDC claims onto the tool's user model, keyed by the stable subject.

    Just-in-time provisioning: the user record is created on first login.
    """

    def filter_users_by_claims(self, claims):
        subject = claims.get("sub")
        if not subject:
            return self.UserModel.objects.none()
        users = self.UserModel.objects.filter(subject=subject)
        if users.exists() or not conf.get("OIDC_MATCH_BY_USERNAME_FALLBACK"):
            return users
        # Subject drift (opt-in): the IdP re-issued its user IDs (re-imported
        # dev realm, realm/IdP migration). The username comes from the same
        # trusted IdP, so fall back to it instead of crashing into the
        # unique-username constraint; update_user persists the new subject.
        username = claims.get(conf.get("OIDC_CLAIM_USERNAME"))
        if username:
            return self.UserModel.objects.filter(username__iexact=username)
        return self.UserModel.objects.none()

    def create_user(self, claims):
        # Optional per-deployment cap on accounts. New identities are turned
        # away once the cap is reached; existing users still log in.
        max_users = conf.get("MAX_USERS")
        if max_users is not None:
            current = _users_counting_toward_cap(self.UserModel).count()
            if current >= max_users:
                logger.warning(
                    "Refusing OIDC account creation: MAX_USERS=%s reached.", max_users
                )
                raise PermissionDenied(
                    "The maximum number of user accounts has been reached."
                )
        user = self.UserModel(
            username=claims.get(conf.get("OIDC_CLAIM_USERNAME")) or claims.get("sub"),
            email=claims.get(conf.get("OIDC_CLAIM_EMAIL"), ""),
            subject=claims.get("sub"),
            first_name=claims.get(conf.get("OIDC_CLAIM_FIRST_NAME"), ""),
            last_name=claims.get(conf.get("OIDC_CLAIM_LAST_NAME"), ""),
            claims=claims or {},
        )
        # Track the login time ourselves — retention jobs key on it, and
        # mozilla-django-oidc doesn't reliably update last_login here.
        user.last_login = timezone.now()
        self._apply_admin_group(user, claims)
        user.save()
        return user

    def update_user(self, user, claims):
        user.email = claims.get(conf.get("OIDC_CLAIM_EMAIL"), user.email)
        user.first_name = claims.get(conf.get("OIDC_CLAIM_FIRST_NAME"), user.first_name)
        user.last_name = claims.get(conf.get("OIDC_CLAIM_LAST_NAME"), user.last_name)
        # Backfill a missing subject, and adopt a re-issued one after a
        # username-fallback match — see filter_users_by_claims.
        if claims.get("sub") and user.subject != claims.get("sub"):
            user.subject = claims.get("sub")
        user.claims = claims or {}
        user.last_login = timezone.now()
        self._apply_admin_group(user, claims)
        user.save()
        return user

    def _apply_admin_group(self, user, claims):
        """Sync Django admin flags with an IdP group claim, if configured.

        When ``OIDC_ADMIN_GROUP`` is set, the IdP group is authoritative for
        OIDC users: membership grants admin, absence revokes it. The local
        ``createsuperuser`` account is a separate identity and is unaffected,
        serving as a break-glass fallback.
        """
        if not conf.get("OIDC_ADMIN_GROUP"):
            return
        is_admin = claims_in_admin_group(claims)
        user.is_staff = is_admin
        user.is_superuser = is_admin


def provider_logout_url(request):
    """Build the provider end-session URL used during OIDC logout."""
    params = {
        "post_logout_redirect_uri": settings.LOGOUT_REDIRECT_URL,
        "client_id": settings.OIDC_RP_CLIENT_ID,
    }
    id_token = request.session.get("oidc_id_token")
    if id_token:
        params["id_token_hint"] = id_token
    return f"{settings.OIDC_OP_LOGOUT_ENDPOINT}?{urlencode(params)}"


def _delete_sessions_for_subject(subject):
    """Delete every active Django session belonging to the OIDC ``subject``.

    Django's DB session store has no index from user to session, so we scan the
    unexpired sessions and match the decoded ``_auth_user_id``. There are only
    ever a handful of live sessions per user, so this stays cheap. Logging out
    by subject (not ``sid``) drops all of the user's sessions, which is exactly
    what a remote SSO logout should do.
    """
    user_ids = {
        str(pk)
        for pk in get_user_model().objects.filter(subject=subject).values_list(
            "pk", flat=True
        )
    }
    if not user_ids:
        return 0
    deleted = 0
    for session in Session.objects.filter(expire_date__gte=timezone.now()):
        if session.get_decoded().get("_auth_user_id") in user_ids:
            session.delete()
            deleted += 1
    return deleted


@csrf_exempt
@require_POST
def backchannel_logout(request):
    """OIDC Back-Channel Logout endpoint.

    The IdP POSTs a signed ``logout_token`` here (server-to-server, no browser
    session) when a user logs out of the SSO; we verify it and drop that user's
    local sessions. CSRF-exempt because the caller is the IdP, not the SPA.
    Configure this URL as the client's "Backchannel logout URL" in the IdP.
    """
    logout_token = request.POST.get("logout_token")
    if not logout_token:
        return HttpResponseBadRequest("missing logout_token")

    # Verify the JWS signature against the provider's JWKS (reuses the auth
    # backend); a token carrying a nonce is rejected here, as the spec requires.
    try:
        payload = OIDCBackend().verify_token(logout_token)
    except Exception as exc:  # noqa: BLE001 — any failure means an invalid token
        logger.warning("Back-channel logout: token verification failed: %s", exc)
        return HttpResponseBadRequest("invalid logout_token")

    # Validate the logout-token claims (OIDC Back-Channel Logout 1.0, §2.4).
    issuer = conf.get("OIDC_OP_ISSUER")
    if issuer and payload.get("iss") != issuer:
        return HttpResponseBadRequest("issuer mismatch")
    audience = payload.get("aud")
    audiences = [audience] if isinstance(audience, str) else (audience or [])
    if settings.OIDC_RP_CLIENT_ID not in audiences:
        return HttpResponseBadRequest("audience mismatch")
    events = payload.get("events")
    if not isinstance(events, dict) or BACKCHANNEL_LOGOUT_EVENT not in events:
        return HttpResponseBadRequest("missing back-channel logout event")
    subject = payload.get("sub")
    if not subject:
        # We key local sessions on the subject; a sid-only token can't be acted on.
        return HttpResponseBadRequest("missing sub")

    deleted = _delete_sessions_for_subject(subject)
    logger.info("Back-channel logout for sub=%s dropped %d session(s)", subject, deleted)
    # Spec: 200 with no caching on success.
    response = HttpResponse(status=200)
    response["Cache-Control"] = "no-store"
    return response
