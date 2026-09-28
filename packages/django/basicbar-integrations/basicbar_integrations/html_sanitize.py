# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""The one HTML allowlist for rich content.

The server is the security boundary: whatever a rich-text editor (or any
client) produces is filtered through this allowlist before it is stored or
rendered server-side. The allowlist mirrors the formatting a basic editor
offers: bold, italic, lists, links, headings (h2/h3) and images. Links may
point anywhere (rel="noopener" is forced); images must come from the app's
own /media/ storage.
"""
import posixpath
from urllib.parse import unquote

import nh3

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "a", "h2", "h3", "img",
}
ALLOWED_ATTRIBUTES = {"a": {"href"}, "img": {"src", "alt"}}
# External links are allowed; images are pinned to /media/ by _attribute_filter.
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


_CONTROL_CHARS = frozenset(chr(c) for c in range(0x20)) | {"\x7f"}  # C0 + DEL


def _has_control_chars(value):
    return any(c in _CONTROL_CHARS for c in value)


def clean_media_url(url):
    """Accept only the app's own media storage: a relative ``/media/…`` path
    whose decoded, normalised form stays inside ``/media/`` — anything else
    becomes "". Percent-encoded dot segments (``%2e%2e``), double encoding
    and backslashes are rejected (basicbar#6), as are C0/DEL control
    characters (e.g. a raw or ``%09``-encoded tab — browsers strip these
    anywhere in a URL before resolving it, so ``normpath`` must never see
    them), a ``?``/``#`` query or fragment (raw or encoded — a trailing
    ``..`` hidden after one is still resolved by the browser; query strings
    on media URLs aren't supported), and anything over 300 characters
    (truncating *after* validation could cut a long, validated path back
    down to a traversal)."""
    url = url or ""
    if len(url) > 300:
        return ""
    if (
        not url.startswith("/media/")
        or url.startswith("//")
        or "\\" in url
        or "?" in url
        or "#" in url
        or _has_control_chars(url)
    ):
        return ""
    decoded = unquote(url)
    if (
        "\\" in decoded
        or "%" in decoded
        or "?" in decoded
        or "#" in decoded
        or _has_control_chars(decoded)
    ):
        return ""
    normalised = posixpath.normpath(decoded)
    if normalised != "/media" and not normalised.startswith("/media/"):
        return ""
    return url


def _attribute_filter(tag, attr, value):
    # Images must be local /media/ URLs; drop any other src (leaves a bare
    # <img>, which the editor never produces). All other attributes pass
    # through the tag/attribute allowlist unchanged.
    if tag == "img" and attr == "src":
        return clean_media_url(value) or None
    return value


def clean_html(html):
    """Sanitize rich HTML down to the supported formatting subset."""
    if not html:
        return ""
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener",
        attribute_filter=_attribute_filter,
    )
