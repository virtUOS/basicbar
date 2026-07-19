# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Generic LTI 1.3 endpoints: OIDC initiation, JWKS, platform management.

The message-launch endpoint itself is tool code — what a launch lands on
(a room, a pool, a course view) is product logic. Tools compose it from the
primitives in :mod:`basicbar_lti.provisioning` and :mod:`.tool_conf`.
"""
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from pylti1p3.contrib.django import DjangoOIDCLogin
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import LtiPlatform
from .provisioning import launch_storage
from .serializers import LtiPlatformSerializer
from .tool_conf import build_tool_conf


@csrf_exempt
def lti_login(request):
    """OIDC third-party initiated login (the platform POSTs/GETs here)."""
    target = request.POST.get(
        "target_link_uri", request.GET.get("target_link_uri")
    )
    if not target:
        return HttpResponse("Missing target_link_uri", status=400)
    oidc_login = DjangoOIDCLogin(
        request, build_tool_conf(), launch_data_storage=launch_storage()
    )
    return oidc_login.redirect(target)


def lti_jwks(request):
    """The tool's public key set (register this URL in the platform)."""
    return JsonResponse(build_tool_conf().get_jwks(), safe=False)


class LtiPlatformViewSet(viewsets.ModelViewSet):
    """Staff-only CRUD for LTI platform registrations (web admin).

    Subclass to change the permission (default: Django staff)."""

    queryset = LtiPlatform.objects.all().order_by("name")
    serializer_class = LtiPlatformSerializer
    permission_classes = [IsAdminUser]


class LtiToolInfoView(APIView):
    """The tool's own LTI endpoints, for pasting into the LMS registration.

    Assumes the conventional ``/lti/…`` paths under ``FRONTEND_BASE_URL``."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        base = settings.FRONTEND_BASE_URL.rstrip("/")
        return Response({
            "login_url": f"{base}/lti/login/",
            "launch_url": f"{base}/lti/launch/",
            "jwks_url": f"{base}/lti/jwks/",
            "icon_url": f"{base}/lti/icon.svg",
        })
