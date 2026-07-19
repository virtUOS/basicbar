# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from django.contrib import admin

from .models import LtiPlatform, LtiToolKey, LtiUserLink


@admin.register(LtiPlatform)
class LtiPlatformAdmin(admin.ModelAdmin):
    list_display = ("name", "issuer", "client_id", "is_active", "link_by_email")
    list_filter = ("is_active", "link_by_email")


@admin.register(LtiUserLink)
class LtiUserLinkAdmin(admin.ModelAdmin):
    list_display = ("platform", "sub", "user")
    search_fields = ("sub", "user__username", "user__email")


@admin.register(LtiToolKey)
class LtiToolKeyAdmin(admin.ModelAdmin):
    list_display = ("__str__", "created_at")
    readonly_fields = ("public_key", "created_at")
    exclude = ("private_key",)
