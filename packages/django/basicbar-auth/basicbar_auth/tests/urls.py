# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.urls import path

from basicbar_auth.oidc import backchannel_logout

urlpatterns = [
    path(
        "oidc/backchannel-logout/",
        backchannel_logout,
        name="oidc-backchannel-logout",
    ),
]
