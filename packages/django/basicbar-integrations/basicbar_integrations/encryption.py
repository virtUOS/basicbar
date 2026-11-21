# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Symmetric encryption for secrets stored at rest (e.g. a GitLab project token).

Needs the extra ``basicbar-integrations[encryption]`` (``cryptography``). Fernet
(AES-128-CBC + HMAC). The key is ``settings.TOKEN_ENCRYPTION_KEY`` when set, otherwise
derived from ``SECRET_KEY``; the derivation is byte-for-byte the one the tools used before,
so tokens stored earlier stay readable. A failed decryption (the key changed) yields an empty
string instead of an error, so a key mismatch switches the feature off rather than breaking
pages. Privacy: neither the plaintext, the ciphertext nor the key is ever logged or put into
an exception message.
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from . import conf

logger = logging.getLogger(__name__)

# A key problem is hit on every request that reads a token: warn once per process and kind.
_warned: set[str] = set()


def _warn_once(kind: str, message: str) -> None:
    if kind not in _warned:
        _warned.add(kind)
        logger.warning(message)


def reset_warnings() -> None:
    """Forget what was already warned about (tests)."""
    _warned.clear()


class EncryptionKeyError(ImproperlyConfigured, ValueError):
    """``TOKEN_ENCRYPTION_KEY`` is set but not a valid Fernet key."""


def _fernet() -> Fernet:
    key = conf.get("TOKEN_ENCRYPTION_KEY")
    if key:
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except ValueError:
            raise EncryptionKeyError("TOKEN_ENCRYPTION_KEY is not a valid Fernet key") from None
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(text: str) -> str:
    """Encrypt to a storable token; empty stays empty."""
    if not text:
        return ""
    return _fernet().encrypt(text.encode()).decode()


def decrypt(token: str) -> str:
    """Decrypt a stored token; empty or undecryptable yields an empty string."""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except EncryptionKeyError:
        _warn_once("key", "TOKEN_ENCRYPTION_KEY is not a valid Fernet key; stored secrets are unreadable.")
        return ""
    except (InvalidToken, ValueError):
        _warn_once("decrypt", "A stored secret could not be decrypted; did TOKEN_ENCRYPTION_KEY change?")
        return ""
