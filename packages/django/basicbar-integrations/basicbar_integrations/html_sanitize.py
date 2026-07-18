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
import nh3

ALLOWED_TAGS = {
    "p", "br", "strong", "b", "em", "i", "ul", "ol", "li", "a", "h2", "h3", "img",
}
ALLOWED_ATTRIBUTES = {"a": {"href"}, "img": {"src", "alt"}}
# External links are allowed; images are pinned to /media/ by _attribute_filter.
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def clean_media_url(url):
    """Accept only the app's own media storage: a relative ``/media/…`` path
    without traversal — anything else becomes ""."""
    url = (url or "").strip()
    if url.startswith("/media/") and ".." not in url and not url.startswith("//"):
        return url[:300]
    return ""


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
