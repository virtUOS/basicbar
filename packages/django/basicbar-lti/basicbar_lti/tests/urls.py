# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Test URL surface: the package endpoints plus a minimal launch view that a
tool would normally implement (composed from the package primitives)."""
from django.http import HttpResponse, JsonResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from pylti1p3.contrib.django import DjangoMessageLaunch
from rest_framework.routers import DefaultRouter

from basicbar_lti.provisioning import (
    is_instructor,
    launch_storage,
    platform_for,
    provision_user,
)
from basicbar_lti.tool_conf import build_tool_conf
from basicbar_lti.views import LtiPlatformViewSet, LtiToolInfoView, lti_jwks, lti_login


@csrf_exempt
def test_launch(request):
    """Tool-shaped launch endpoint built from the package primitives."""
    message_launch = DjangoMessageLaunch(
        request, build_tool_conf(), launch_data_storage=launch_storage()
    )
    launch_data = message_launch.get_launch_data()
    platform = platform_for(launch_data)
    if platform is None:
        return JsonResponse({"error": "unknown platform"}, status=403)
    if is_instructor(launch_data):
        user = provision_user(platform, launch_data)
        return JsonResponse({"instructor": True, "user": user.pk})
    return JsonResponse({"instructor": False})


def embeddable_page(request):
    return HttpResponse("<html><body>embed me</body></html>")


router = DefaultRouter()
router.register("platforms", LtiPlatformViewSet, basename="lti-platform")

urlpatterns = [
    path("lti/login/", lti_login, name="lti-login"),
    path("lti/launch/", test_launch, name="lti-launch"),
    path("lti/jwks/", lti_jwks, name="lti-jwks"),
    path("lti/page/", embeddable_page, name="lti-test-page"),
    path("api/lti/tool-info/", LtiToolInfoView.as_view(), name="lti-tool-info"),
    path("api/lti/", include(router.urls)),
]
