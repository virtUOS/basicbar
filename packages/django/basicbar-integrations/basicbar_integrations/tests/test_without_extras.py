# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""A tool that installs the package without the extras must still start and pass ``check``."""

import os
import subprocess
import sys
import textwrap

from django.test import SimpleTestCase

SCRIPT = textwrap.dedent(
    """
    import os, sys
    sys.modules["httpx"] = None
    sys.modules["cryptography"] = None
    os.environ["DJANGO_SETTINGS_MODULE"] = "basicbar_integrations.tests.settings"
    if os.environ.get("KEY"):
        from django.conf import settings
        settings.TOKEN_ENCRYPTION_KEY = os.environ["KEY"]
    import django
    django.setup()
    from django.core.management import call_command
    from django.core.management.base import SystemCheckError
    try:
        call_command("check")
    except SystemCheckError as exc:
        sys.stderr.write(str(exc))
        sys.exit(1)
    """
)


def run_check(key: str = "") -> subprocess.CompletedProcess:
    env = {**os.environ, "KEY": key}
    return subprocess.run(
        [sys.executable, "-I", "-c", SCRIPT],
        capture_output=True, text=True, env=env, timeout=120,
    )


class WithoutExtrasTests(SimpleTestCase):
    def test_app_and_checks_run_without_extras(self):
        result = run_check()
        self.assertEqual(result.returncode, 0, result.stderr)

        result = run_check("secret-key-value")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("basicbar_integrations.E001", result.stderr)
        self.assertIn("basicbar-integrations[encryption]", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertNotIn("ImportError", result.stderr)
        self.assertNotIn("secret-key-value", result.stderr + result.stdout)
