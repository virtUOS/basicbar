# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""HTTP endpoints for the optional integrations.

The canonical translate contract of the -bar tools:
``POST {text, source, target, format?}`` → ``{translated}``. Tools that need
a different permission subclass the view and wire their own URL.
"""

from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import html_sanitize, translation_service


class TranslateView(APIView):
    """Machine-translate a snippet for the editor's pre-fill.

    For signed-in authors, to fill an empty translation field with a
    machine-translated draft (never auto-applied — the caller decides whether
    to keep it). Off unless a provider is configured; returns 503 in that case
    so the frontend can hide/disable the affordance. ``format=html`` results
    are sanitized server-side before they are returned.
    """

    permission_classes = [IsAuthenticated]

    def clean_html(self, html: str) -> str:
        """Sanitize an HTML translation result; override to change the policy."""
        return html_sanitize.clean_html(html)

    def post(self, request):
        if not translation_service.is_enabled():
            return Response({"detail": "Translation is not configured."}, status=503)
        text = str(request.data.get("text", ""))
        source = str(request.data.get("source", ""))
        target = str(request.data.get("target", ""))
        fmt = str(request.data.get("format", "text"))
        languages = dict(settings.LANGUAGES)
        if source not in languages or target not in languages:
            return Response({"detail": "Unknown language."}, status=400)
        try:
            translated = translation_service.translate(
                text, source, target, html=(fmt == "html")
            )
        except translation_service.TranslationError as exc:
            return Response({"detail": f"Translation failed: {exc}"}, status=502)
        if fmt == "html":
            translated = self.clean_html(translated)
        return Response({"translated": translated})
