# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Settings access with package defaults."""

from django.conf import settings

DEFAULTS = {
    # HTML paths that may be embedded by registered LMS platforms (the
    # frame-ancestors middleware acts only under these prefixes). Tools add
    # their embeddable surfaces, e.g. abstimmbar: ("/lti/", "/p/").
    "LTI_FRAME_PATH_PREFIXES": ("/lti/",),
}


def get(name: str):
    """Return the project's setting, or the package default when unset."""
    return getattr(settings, name, DEFAULTS[name])
