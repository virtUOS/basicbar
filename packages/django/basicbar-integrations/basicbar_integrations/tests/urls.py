# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.urls import include, path

from .test_metrics import _View as MetricsTestView

urlpatterns = [
    path("api/", include("basicbar_integrations.urls")),
    path("metrics", MetricsTestView.as_view()),
]
