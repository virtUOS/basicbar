# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.urls import path

from .views import CapabilitiesView, TranslateView

urlpatterns = [
    path("translate/", TranslateView.as_view(), name="basicbar-translate"),
    path("capabilities/", CapabilitiesView.as_view(), name="basicbar-capabilities"),
]
