# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

# Schema-identisch zu abstimmbars historischen lti/0001+0002 (mit den
# Standard-Tabellennamen des Pakets); Bestands-Deployments ziehen ihre Daten
# per Umzugsmigration um — siehe README bzw. abstimmbars lti/0003.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LtiToolKey",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("private_key", models.TextField()),
                ("public_key", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="LtiPlatform",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(help_text="Anzeigename, z. B. „Moodle Uni OS“", max_length=200)),
                ("issuer", models.CharField(max_length=500)),
                ("client_id", models.CharField(max_length=255)),
                ("auth_login_url", models.URLField(max_length=500)),
                ("auth_token_url", models.URLField(max_length=500)),
                ("key_set_url", models.URLField(blank=True, max_length=500)),
                ("key_set", models.JSONField(blank=True, null=True)),
                ("deployment_ids", models.JSONField(default=list)),
                ("is_active", models.BooleanField(default=True)),
                ("link_by_email", models.BooleanField(default=False, help_text="Beim ersten Launch unbekannte LTI-Nutzer über die E-Mail-Adresse mit bestehenden Konten verknüpfen (nur für vertrauenswürdige Plattformen aktivieren).")),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("issuer", "client_id"), name="basicbar_lti_unique_platform")
                ],
            },
        ),
        migrations.CreateModel(
            name="LtiUserLink",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("sub", models.CharField(max_length=255)),
                ("platform", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_links", to="basicbar_lti.ltiplatform")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="lti_links", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "constraints": [
                    models.UniqueConstraint(fields=("platform", "sub"), name="basicbar_lti_one_user_per_sub")
                ],
            },
        ),
    ]
