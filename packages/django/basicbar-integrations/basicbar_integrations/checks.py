# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""System checks of the app. ``cryptography`` is imported only when the setting is used."""

from django.core.checks import Error

from . import conf


def token_encryption_key_check(app_configs, **kwargs):
    if not conf.get("TOKEN_ENCRYPTION_KEY"):
        return []
    try:
        from .encryption import EncryptionKeyError, _fernet
    except ImportError:
        return [
            Error(
                "TOKEN_ENCRYPTION_KEY is set but the 'cryptography' package is not installed.",
                hint="Install the extra: pip install 'basicbar-integrations[encryption]'",
                id="basicbar_integrations.E001",
            )
        ]
    try:
        _fernet()
    except EncryptionKeyError:
        return [
            Error(
                "TOKEN_ENCRYPTION_KEY is set but not a valid Fernet key.",
                hint=(
                    "Generate one with: python -c \"from cryptography.fernet "
                    "import Fernet; print(Fernet.generate_key().decode())\""
                ),
                id="basicbar_integrations.E001",
            )
        ]
    return []
