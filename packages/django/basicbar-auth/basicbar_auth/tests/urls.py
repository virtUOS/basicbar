# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.urls import include, path

from basicbar_auth.views import whoami

urlpatterns = [
    path("", include("basicbar_auth.urls")),
    path("api/whoami/", whoami),
]
