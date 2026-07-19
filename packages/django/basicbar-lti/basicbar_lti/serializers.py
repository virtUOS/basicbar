# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Serializer for staff LTI-platform management. Never exposes key material
(private_key / key_set); those stay Django-admin-only."""
from rest_framework import serializers

from .models import LtiPlatform


class LtiPlatformSerializer(serializers.ModelSerializer):
    deployment_ids = serializers.ListField(
        child=serializers.CharField(allow_blank=True), required=False, default=list
    )

    class Meta:
        model = LtiPlatform
        fields = [
            "id", "name", "issuer", "client_id",
            "auth_login_url", "auth_token_url", "key_set_url",
            "deployment_ids", "link_by_email", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_deployment_ids(self, value):
        return [str(v).strip() for v in (value or []) if str(v).strip()]

    def validate(self, attrs):
        issuer = attrs.get("issuer", getattr(self.instance, "issuer", None))
        client_id = attrs.get("client_id", getattr(self.instance, "client_id", None))
        qs = LtiPlatform.objects.filter(issuer=issuer, client_id=client_id)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError(
                "Eine Plattform mit diesem Issuer und dieser Client-ID "
                "existiert bereits."
            )
        return attrs
