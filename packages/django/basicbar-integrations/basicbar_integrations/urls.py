# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.urls import path

from .views import TranslateView

urlpatterns = [
    path("translate/", TranslateView.as_view(), name="basicbar-translate"),
]
