# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Minimal Django settings to run the package test suite standalone."""

SECRET_KEY = "test-only-not-a-secret"
DEBUG = True

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "rest_framework",
    "basicbar_lti",
    "basicbar_lti.tests",
]

MIDDLEWARE = [
    "basicbar_lti.middleware.LtiFrameAncestorsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
}

AUTH_USER_MODEL = "basicbar_lti_tests.TestUser"

ROOT_URLCONF = "basicbar_lti.tests.urls"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FRONTEND_BASE_URL = "http://testserver"
