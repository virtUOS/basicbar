# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.urls import include, path

from .views import DemoMetricsView

urlpatterns = [
    path("api/", include("basicbar_integrations.urls")),
    path("metrics", DemoMetricsView.as_view()),
]
