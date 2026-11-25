# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Dynamic Registration logic: validate the platform's OpenID configuration,
build the tool registration payload, register and create the platform."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from . import conf
from .dynreg_http import RegistrationError, request_json
from .models import LtiPlatform, LtiRegistrationToken

LTI_TOOL_CONFIG = "https://purl.imsglobal.org/spec/lti-tool-configuration"
LTI_PLATFORM_CONFIG = "https://purl.imsglobal.org/spec/lti-platform-configuration"

_REQUIRED = (
    "issuer",
    "authorization_endpoint",
    "token_endpoint",
    "jwks_uri",
    "registration_endpoint",
)
_ENDPOINTS = (
    "authorization_endpoint",
    "token_endpoint",
    "jwks_uri",
    "registration_endpoint",
)


# config field -> LtiPlatform column it is stored in (length limits come
# from the model, SQLite would not enforce them).
_COLUMNS = {
    "issuer": "issuer",
    "authorization_endpoint": "auth_login_url",
    "token_endpoint": "auth_token_url",
    "jwks_uri": "key_set_url",
}


def _max_len(column: str) -> int:
    return LtiPlatform._meta.get_field(column).max_length


@dataclass(frozen=True)
class PlatformConfig:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    jwks_uri: str
    registration_endpoint: str
    product_family_code: str = ""


def _netloc(url: str) -> str:
    return urlsplit(url).netloc.lower()


def load_platform_config(
    config_url: str, registration_token: str | None
) -> PlatformConfig:
    """Fetch and validate the platform's OpenID configuration."""
    data = request_json(config_url, bearer=registration_token)
    for key in _REQUIRED:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise RegistrationError(
                "Die Konfiguration der Plattform ist unvollständig.",
                f"missing or invalid field {key!r}",
            )
    for key, column in _COLUMNS.items():
        if len(data[key]) > _max_len(column):
            raise RegistrationError(
                "Die Konfiguration der Plattform enthält zu lange Werte.",
                f"{key} longer than {_max_len(column)} characters",
            )
    issuer = data["issuer"]
    iss, cfg = urlsplit(issuer), urlsplit(config_url)
    if (
        iss.scheme.lower() != cfg.scheme.lower()
        or iss.netloc.lower() != cfg.netloc.lower()
        or not cfg.path.startswith(iss.path.rstrip("/"))
    ):
        raise RegistrationError(
            "Die Konfigurationsadresse passt nicht zur Kennung (issuer) der Plattform.",
            f"config_url={config_url!r} issuer={issuer!r}",
        )
    for key in _ENDPOINTS:
        if _netloc(data[key]) != iss.netloc.lower():
            raise RegistrationError(
                "Die Plattform nennt Endpunkte auf einem anderen Server; "
                "das wird nicht akzeptiert.",
                f"{key}={data[key]!r} issuer={issuer!r}",
            )
    block = data.get(LTI_PLATFORM_CONFIG)
    family = block.get("product_family_code") if isinstance(block, dict) else ""
    return PlatformConfig(
        issuer=issuer,
        authorization_endpoint=data["authorization_endpoint"],
        token_endpoint=data["token_endpoint"],
        jwks_uri=data["jwks_uri"],
        registration_endpoint=data["registration_endpoint"],
        product_family_code=family if isinstance(family, str) else "",
    )


def tool_urls(request) -> dict:
    return {
        key: request.build_absolute_uri(reverse(name))
        for key, name in (
            ("login", "lti-login"),
            ("launch", "lti-launch"),
            ("jwks", "lti-jwks"),
            ("register", "lti-register"),
        )
    }


def tool_registration_payload(request) -> dict:
    """The registration request body announcing this tool to the platform."""
    urls = tool_urls(request)
    settings_ = conf.tool_registration()
    logo_uri = ""
    if settings_["logo_path"]:
        logo_uri = request.build_absolute_uri(settings_["logo_path"])
    if not conf.get("LTI_REGISTRATION_ALLOW_HTTP"):
        checked = [urls["login"], urls["launch"], urls["jwks"]]
        if logo_uri:
            checked.append(logo_uri)
        if any(not u.lower().startswith("https://") for u in checked):
            raise RegistrationError(
                "Die Adressen dieses Tools sind nicht per https erreichbar. "
                "Bitte den Betreiber informieren (Proxy-Konfiguration: "
                "SECURE_PROXY_SSL_HEADER).",
                f"non-https tool URLs: {checked}",
            )
    launch = urls["launch"]
    messages = [
        {**m, "target_link_uri": m.get("target_link_uri") or launch}
        for m in settings_["messages"]
    ]
    payload = {
        "application_type": "web",
        "response_types": ["id_token"],
        "grant_types": ["implicit", "client_credentials"],
        "initiate_login_uri": urls["login"],
        "redirect_uris": [launch],
        "client_name": settings_["client_name"],
        "jwks_uri": urls["jwks"],
        "token_endpoint_auth_method": "private_key_jwt",
        "scope": settings_["scope"],
        LTI_TOOL_CONFIG: {
            "domain": urlsplit(launch).netloc,
            "target_link_uri": launch,
            "claims": list(settings_["claims"]),
            "description": settings_["description"],
            "custom_parameters": dict(settings_["custom_parameters"]),
            "messages": messages,
        },
    }
    if logo_uri:
        payload["logo_uri"] = logo_uri
    return payload


def known_issuer(config: PlatformConfig) -> bool:
    issuer = config.issuer.rstrip("/")
    return any(
        p.issuer.rstrip("/") == issuer
        for p in LtiPlatform.objects.filter(is_active=True)
    )


def register_platform(
    request,
    token: LtiRegistrationToken,
    config: PlatformConfig,
    registration_token: str | None,
) -> LtiPlatform:
    """Register at the platform, create the ``LtiPlatform`` and consume the
    token in one transaction; any failure leaves the token open."""
    try:
        return _register(request, token, config, registration_token)
    except IntegrityError as exc:
        raise RegistrationError(
            "Diese Plattform ist bereits mit diesem Tool registriert.",
            f"IntegrityError: {exc}",
        ) from exc


def _register(request, token, config, registration_token) -> LtiPlatform:
    with transaction.atomic():
        locked = LtiRegistrationToken.objects.select_for_update().get(pk=token.pk)
        if locked.used_at is not None or locked.expires_at <= timezone.now():
            raise RegistrationError("Link bereits verwendet oder abgelaufen.")
        response = request_json(
            config.registration_endpoint,
            bearer=registration_token,
            payload=tool_registration_payload(request),
        )
        client_id = response.get("client_id")
        if not isinstance(client_id, str) or not client_id:
            raise RegistrationError(
                "Die Plattform hat keine client_id geliefert.",
                f"response keys: {sorted(response)}",
            )
        if len(client_id) > _max_len("client_id"):
            raise RegistrationError(
                "Die Plattform hat eine zu lange client_id geliefert.",
                f"client_id longer than {_max_len('client_id')} characters",
            )
        block = response.get(LTI_TOOL_CONFIG)
        deployment_id = block.get("deployment_id") if isinstance(block, dict) else None
        deployment_ids = [str(deployment_id)] if deployment_id not in (None, "") else []
        host = urlsplit(config.issuer).hostname or config.issuer
        platform = LtiPlatform.objects.create(
            name=(
                locked.note or f"{config.product_family_code or 'LMS'} ({host})"
            )[: _max_len("name")],
            issuer=config.issuer,
            client_id=client_id,
            auth_login_url=config.authorization_endpoint,
            auth_token_url=config.token_endpoint,
            key_set_url=config.jwks_uri,
            deployment_ids=deployment_ids,
            is_active=True,
            link_by_email=False,
        )
        locked.used_at = timezone.now()
        locked.platform = platform
        locked.save(update_fields=["used_at", "platform"])
    return platform
