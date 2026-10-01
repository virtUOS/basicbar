# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Optional machine translation for the content editor.

A pluggable provider pre-fills empty translations from the canonical value. It
is off by default; an institution can self-host LibreTranslate (Apache-2.0) and
point ``LIBRETRANSLATE_URL`` at it. The provider only ever produces an editable
draft — callers decide whether to keep it. Uses the stdlib ``urllib`` so it adds
no dependency.
"""

import json
from urllib import error, request

from . import conf
from ._http import TRANSPORT_ERRORS, http_error_detail


class TranslationError(Exception):
    """A translation could not be produced (provider off or upstream failure)."""


def is_enabled() -> bool:
    """Whether a usable translation provider is configured."""
    provider = conf.get("CONTENT_TRANSLATION_PROVIDER")
    if provider == "libretranslate":
        return bool(conf.get("LIBRETRANSLATE_URL"))
    return False


def translate(text: str, source: str, target: str, *, html: bool = False) -> str:
    """Translate ``text`` from ``source`` to ``target`` via the provider.

    ``html=True`` tells the provider ``text`` is HTML (e.g. rich-text fields)
    so it preserves markup instead of escaping it.

    Returns the original text unchanged when it is blank or the languages match.
    Raises ``TranslationError`` if no provider is configured or the upstream
    call fails.
    """
    if not text or not text.strip() or source == target:
        return text
    if not is_enabled():
        raise TranslationError("No translation provider is configured.")
    return _libretranslate(text, source, target, html=html)


def _libretranslate(text: str, source: str, target: str, *, html: bool = False) -> str:
    payload = {
        "q": text,
        "source": source,
        "target": target,
        "format": "html" if html else "text",
    }
    if conf.get("LIBRETRANSLATE_API_KEY"):
        payload["api_key"] = conf.get("LIBRETRANSLATE_API_KEY")
    url = conf.get("LIBRETRANSLATE_URL").rstrip("/") + "/translate"
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        # A 4xx carries the actual cause in its body ("en is not supported");
        # that is a configuration problem, not an outage.
        detail = http_error_detail(exc)
        raise TranslationError(
            f"Translation service returned HTTP {exc.code}"
            + (f": {detail}" if detail else "")
        ) from exc
    except TRANSPORT_ERRORS as exc:
        raise TranslationError(f"Translation service unavailable: {exc}") from exc
    if not isinstance(data, dict):
        raise TranslationError("Translation service returned an unexpected response.")
    translated = data.get("translatedText")
    if not translated:
        raise TranslationError("Translation service returned no text.")
    return translated
