# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""LTI 1.3 platform registrations and the tool keypair.

One tool keypair for all platforms; platforms are registered by admins
(Django admin or the staff API). What an LMS course context maps onto is
tool logic — a tool defines its own context-link model with a FK onto
``basicbar_lti.LtiPlatform`` (e.g. abstimmbar's ``LtiContextLink`` → Room).

The ``db_table`` names keep the historical ``lti_*`` prefix so existing
deployments adopt the package with a state-only migration plus
``migrate --fake-initial`` — no table rename needed.
"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    """Adds created/updated timestamps (mirror of the tools' convention)."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LtiToolKey(models.Model):
    """The tool's RSA keypair (singleton, auto-generated on first use)."""

    private_key = models.TextField()
    public_key = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "lti_ltitoolkey"

    @classmethod
    def load(cls):
        key = cls.objects.first()
        if key is None:
            private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            key = cls.objects.create(
                private_key=private.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption(),
                ).decode(),
                public_key=private.public_key()
                .public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.SubjectPublicKeyInfo,
                )
                .decode(),
            )
        return key

    def __str__(self):
        return f"Tool key #{self.pk}"


class LtiPlatform(TimeStampedModel):
    """One LMS platform registration (issuer + client_id)."""

    name = models.CharField(max_length=200, help_text="Anzeigename, z. B. „Moodle Uni OS“")
    issuer = models.CharField(max_length=500)
    client_id = models.CharField(max_length=255)
    auth_login_url = models.URLField(max_length=500)
    auth_token_url = models.URLField(max_length=500)
    key_set_url = models.URLField(max_length=500, blank=True)
    # Alternative to key_set_url (e.g. air-gapped setups, tests): the
    # platform's JWKS pasted inline.
    key_set = models.JSONField(null=True, blank=True)
    deployment_ids = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    # Opt-in account unification: on the first launch of an unknown LTI
    # subject, link to the existing (OIDC) user with the same e-mail instead
    # of creating a duplicate account. Off by default — it makes the platform
    # authoritative for account linking, so enable it only for platforms
    # whose e-mail claims you trust.
    link_by_email = models.BooleanField(
        default=False,
        help_text=(
            "Beim ersten Launch unbekannte LTI-Nutzer über die E-Mail-Adresse "
            "mit bestehenden Konten verknüpfen (nur für vertrauenswürdige "
            "Plattformen aktivieren)."
        ),
    )

    class Meta:
        db_table = "lti_ltiplatform"
        constraints = [
            models.UniqueConstraint(
                fields=["issuer", "client_id"], name="unique_platform_registration"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.issuer})"


class LtiUserLink(TimeStampedModel):
    """Platform-scoped LTI subject ↔ local user.

    The LTI ``sub`` is platform-local and never equals the OIDC subject,
    so unification needs an explicit mapping. A link is written on the
    first launch (whether the user was matched by e-mail or newly
    created) and is authoritative from then on — later e-mail changes in
    the LMS cannot re-route an established account.
    """

    platform = models.ForeignKey(
        LtiPlatform, on_delete=models.CASCADE, related_name="user_links"
    )
    sub = models.CharField(max_length=255)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lti_links"
    )

    class Meta:
        db_table = "lti_ltiuserlink"
        constraints = [
            models.UniqueConstraint(
                fields=["platform", "sub"], name="one_user_per_lti_subject"
            )
        ]

    def __str__(self):
        return f"{self.platform.name}:{self.sub} → {self.user}"
