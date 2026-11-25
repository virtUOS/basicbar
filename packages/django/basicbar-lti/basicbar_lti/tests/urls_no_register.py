# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Test URLconf of a tool that has not wired ``lti-register`` yet."""
from .urls import urlpatterns as _all

urlpatterns = [p for p in _all if getattr(p, "name", None) != "lti-register"]
