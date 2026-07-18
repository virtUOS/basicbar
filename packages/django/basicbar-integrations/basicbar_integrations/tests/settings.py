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
    "basicbar_integrations",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

DATABASES = {
    "default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}
}

ROOT_URLCONF = "basicbar_integrations.tests.urls"
USE_TZ = True

LANGUAGES = [("de", "Deutsch"), ("en", "English")]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
