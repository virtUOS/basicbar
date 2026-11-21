# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Real RS256 tokens for tests that exercise mozilla-django-oidc's verification.

Only usable when mozilla-django-oidc verifies with PyJWT (5.x); with 4.x
(josepy) the tests that need them are skipped via ``requires_pyjwt``.
"""
import functools
import time
import unittest

from mozilla_django_oidc import auth as mozilla_auth

try:
    import jwt
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
except ImportError:  # mozilla-django-oidc 4.x without PyJWT
    jwt = None

requires_pyjwt = unittest.skipUnless(
    jwt is not None and hasattr(mozilla_auth, "jwt"),
    "mozilla-django-oidc does not verify with PyJWT (4.x)",
)


KID = "test-key"


@functools.cache
def _private_key(name):
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def public_key_pem(name="idp") -> str:
    """A key's public half, as ``OIDC_RP_IDP_SIGN_KEY`` takes it. Tokens are
    signed with ``"idp"``; any other name gives an unrelated key."""
    return (
        _private_key(name)
        .public_key()
        .public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )


def jwks() -> dict:
    """The JWKS document an IdP would serve for the signing key."""
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(_private_key("idp").public_key(), as_dict=True)
    return {"keys": [{**jwk, "kid": KID, "alg": "RS256", "use": "sig"}]}


def make_token(claims, *, exp_in=300, iat_in=0) -> str:
    """Sign ``claims`` with RS256; ``exp``/``iat`` are offsets from now."""
    now = int(time.time())
    payload = {"iat": now + iat_in, "exp": now + exp_in, **claims}
    return jwt.encode(payload, _private_key("idp"), algorithm="RS256", headers={"kid": KID})
