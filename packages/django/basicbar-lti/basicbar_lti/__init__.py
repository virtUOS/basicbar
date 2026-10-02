# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

from importlib.metadata import PackageNotFoundError, version

# Single source of truth is pyproject.toml; an uninstalled checkout (e.g. the
# package tests run straight from the tree) reports a dev marker instead.
try:
    __version__ = version("basicbar-lti")
except PackageNotFoundError:  # pragma: no cover
    __version__ = "0.0.0.dev0"
