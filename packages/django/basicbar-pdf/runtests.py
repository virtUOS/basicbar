# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Standalone test runner: ``python runtests.py`` (needs reportlab + pypdf, no Django)."""

import os
import sys
import unittest


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    suite = unittest.defaultTestLoader.discover(os.path.join(root, "basicbar_pdf", "tests"), top_level_dir=root)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
