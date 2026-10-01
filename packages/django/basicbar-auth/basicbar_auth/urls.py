# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""The OIDC and session routes every tool wires the same way::

    path("", include("basicbar_auth.urls")),
    path("api/whoami/", whoami),  # the tool's own (or basicbar_auth.views.whoami)

``api/whoami/`` is deliberately not included: most tools add fields to it.
"""
from django.urls import include, path

from .oidc import SafeOIDCCallbackView, SilentLoginView, backchannel_logout
from .views import logout_view, set_language

urlpatterns = [
    path("oidc/logout-redirect/", logout_view, name="spa-logout"),
    path("oidc/silent/", SilentLoginView.as_view(), name="oidc-silent"),
    path("oidc/backchannel-logout/", backchannel_logout, name="oidc-backchannel-logout"),
    # Must precede mozilla's include: same URL, and the first match wins.
    path(
        "oidc/callback/",
        SafeOIDCCallbackView.as_view(),
        name="oidc_authentication_callback",
    ),
    path("oidc/", include("mozilla_django_oidc.urls")),
    path("api/whoami/language/", set_language, name="whoami-language"),
]
