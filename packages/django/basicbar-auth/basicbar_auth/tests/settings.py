# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Minimal Django settings to run the package test suite standalone."""

SECRET_KEY = "test-only-not-a-secret"
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "basicbar_auth",
    "basicbar_auth.tests",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
}

AUTH_USER_MODEL = "basicbar_auth_tests.TestUser"

AUTHENTICATION_BACKENDS = [
    "basicbar_auth.oidc.OIDCBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "basicbar_auth.tests.urls"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# mozilla-django-oidc client settings the backend expects to exist.
OIDC_RP_CLIENT_ID = "test-client"
OIDC_RP_CLIENT_SECRET = "test-secret"
OIDC_OP_AUTHORIZATION_ENDPOINT = "https://idp.test/auth"
OIDC_OP_TOKEN_ENDPOINT = "https://idp.test/token"
OIDC_OP_USER_ENDPOINT = "https://idp.test/userinfo"
OIDC_OP_JWKS_ENDPOINT = "https://idp.test/jwks"
OIDC_OP_LOGOUT_ENDPOINT = "https://idp.test/logout"
OIDC_RP_SIGN_ALGO = "RS256"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
