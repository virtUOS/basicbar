# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.urls import include, path

urlpatterns = [
    path("api/", include("basicbar_integrations.urls")),
]
