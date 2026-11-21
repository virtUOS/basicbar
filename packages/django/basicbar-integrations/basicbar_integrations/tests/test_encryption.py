# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from basicbar_integrations.checks import token_encryption_key_check
from basicbar_integrations.encryption import (
    EncryptionKeyError,
    decrypt,
    encrypt,
    reset_warnings,
)

LOGGER = "basicbar_integrations.encryption"

# Golden ciphertexts: produced by orientierBAR's unchanged ``common.encryption.encrypt``
# (identical to ansehBAR's apart from a comment in ``_fernet``) for the plaintext
# ``glpat-golden``. They pin that tokens stored before the switch to the package stay readable.
#   A: TOKEN_ENCRYPTION_KEY="", SECRET_KEY="test-only-not-a-secret"  (key derived from SECRET_KEY)
#   B: TOKEN_ENCRYPTION_KEY=GOLDEN_KEY                                (explicit Fernet key)
GOLDEN_PLAINTEXT = "glpat-golden"
GOLDEN_A = "gAAAAABrAgrWkQwqVzMt2kIoNdUMpD7RF2cpoZEtWePED2tJ03S2XEGYRWyPNlkOqttaZSHC9SnK1D6fgqErlm_D1Oxc72dH7w=="
GOLDEN_KEY = "fKi0xjFbqRz2kGx6mPpq3oQ8fXr0m3ZtYw5uJc1Vd9A="  # test value only
GOLDEN_B = "gAAAAABrAgrWjZUKQoOkVE9y_V8vaNnnaFFT9VnayiVw42Q9K5l53zmZwIMm13zbUjGqWJFpNcxg2RDWzNMi9imF3RIQGmDIdA=="


class EncryptionTests(SimpleTestCase):
    def setUp(self):
        reset_warnings()

    def test_golden_ciphertext_from_secret_key(self):
        with override_settings(TOKEN_ENCRYPTION_KEY="", SECRET_KEY="test-only-not-a-secret"):
            self.assertEqual(decrypt(GOLDEN_A), GOLDEN_PLAINTEXT)

    def test_golden_ciphertext_from_token_key(self):
        with override_settings(TOKEN_ENCRYPTION_KEY=GOLDEN_KEY, SECRET_KEY="irrelevant"):
            self.assertEqual(decrypt(GOLDEN_B), GOLDEN_PLAINTEXT)

    def test_warns_once_per_process(self):
        with self.assertLogs(LOGGER, "WARNING") as logs:
            for _ in range(3):
                self.assertEqual(decrypt("gAAAAnot-a-token"), "")
        self.assertEqual(len(logs.output), 1)

    def test_roundtrip_and_empty(self):
        token = encrypt("glpat-abc")
        self.assertNotIn("glpat-abc", token)
        self.assertEqual(decrypt(token), "glpat-abc")
        self.assertEqual((encrypt(""), decrypt("")), ("", ""))

    def test_other_key_gives_empty_and_a_content_free_log(self):
        with override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            token = encrypt("glpat-abc")
        with override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            with self.assertLogs(LOGGER, "WARNING") as logs:
                self.assertEqual(decrypt(token), "")
        self.assertNotIn("glpat-abc", "\n".join(logs.output))
        self.assertNotIn(token, "\n".join(logs.output))

    def test_key_derived_from_secret_key_when_unset(self):
        with override_settings(TOKEN_ENCRYPTION_KEY="", SECRET_KEY="one"):
            token = encrypt("x")
            self.assertEqual(decrypt(token), "x")
        with override_settings(TOKEN_ENCRYPTION_KEY="", SECRET_KEY="two"):
            with self.assertLogs(LOGGER, "WARNING"):
                self.assertEqual(decrypt(token), "")

    def test_invalid_key_raises_on_encrypt_and_degrades_on_decrypt(self):
        self.assertTrue(issubclass(EncryptionKeyError, ImproperlyConfigured))
        self.assertTrue(issubclass(EncryptionKeyError, ValueError))
        with override_settings(TOKEN_ENCRYPTION_KEY="nope-secret-key-value"):
            with self.assertRaises(EncryptionKeyError) as ctx:
                encrypt("x")
            self.assertNotIn("nope-secret-key-value", str(ctx.exception))
            with self.assertLogs(LOGGER, "WARNING") as logs:
                self.assertEqual(decrypt("gAAAA"), "")
            self.assertNotIn("nope-secret-key-value", "\n".join(logs.output))

    def test_check_silent_without_key(self):
        with override_settings(TOKEN_ENCRYPTION_KEY=""):
            self.assertEqual(token_encryption_key_check(None), [])
        with override_settings(TOKEN_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            self.assertEqual(token_encryption_key_check(None), [])

    def test_check_reports_invalid_key_without_value(self):
        with override_settings(TOKEN_ENCRYPTION_KEY="nope-secret-key-value"):
            (error,) = token_encryption_key_check(None)
        self.assertEqual(error.id, "basicbar_integrations.E001")
        self.assertIn("Fernet.generate_key", error.hint)
        self.assertNotIn("nope-secret-key-value", f"{error.msg} {error.hint}")
