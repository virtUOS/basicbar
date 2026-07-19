# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Standalone test runner: ``python runtests.py`` (needs Django, DRF, PyLTI1p3)."""

import os
import sys

import django
from django.test.runner import DiscoverRunner


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "basicbar_lti.tests.settings")
    django.setup()
    failures = DiscoverRunner(verbosity=1).run_tests(["basicbar_lti"])
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
