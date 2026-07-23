# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)

"""Stale-translation tracking for translatable content.

Editors translate a field once — and later edits to one language silently
leave the other behind. These helpers keep, per field, a snapshot of the
last *known-synchronous* state as content hashes, so tools can mark stale
translations in the editor and block/warn in their release processes.

State shape (one JSON dict per model instance — tools add the column
themselves, one line plus migration)::

    translation_sync = models.JSONField(default=dict, blank=True)
    # {"title": {"de": "<hash>", "en": "<hash>"}, "body": {...}}

Record the state whenever the languages are known to be synchronous:
after a machine-translation pre-fill (``onTranslated`` in @basicbar/ui),
or when the author explicitly confirms ("Als aktuell markieren").

Staleness rule (deliberate, keep it explainable): **a language is stale
when its text is unchanged while another language changed since the last
recorded sync.** If every language changed, nothing is marked — that was
a conscious edit of all of them. A field without a recorded state is
never marked (no baseline, e.g. legacy content).
"""

import hashlib


def content_hash(text) -> str:
    """Short, stable hash of a text value (None-safe, whitespace-trimmed)."""
    normalized = (text or "").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def record_synced(state, field, values) -> dict:
    """Return a copy of ``state`` with ``field`` recorded as in-sync now.

    ``values`` maps language code → current text (``{"de": …, "en": …}``).
    """
    new_state = dict(state or {})
    new_state[field] = {lang: content_hash(text) for lang, text in values.items()}
    return new_state


def changed_languages(state, field, values) -> list:
    """Languages whose current text differs from the recorded sync state.

    Empty when no state was recorded for ``field`` (no baseline).
    """
    recorded = (state or {}).get(field)
    if not recorded:
        return []
    return [
        lang
        for lang in recorded
        if content_hash(values.get(lang)) != recorded[lang]
    ]


def stale_languages(state, field, values) -> list:
    """Languages whose translation is potentially outdated for ``field``.

    Stale = unchanged (and non-empty) while at least one other language
    changed since the recorded sync. All languages changed → nothing stale.
    """
    changed = changed_languages(state, field, values)
    if not changed:
        return []
    recorded = (state or {}).get(field) or {}
    return [
        lang
        for lang in recorded
        if lang not in changed and (values.get(lang) or "").strip()
    ]


def stale_map(state, fields_values) -> dict:
    """``{field: [stale langs]}`` over many fields, omitting clean fields.

    ``fields_values`` maps field name → ``{lang: text}``. Handy for
    serializers (expose as e.g. ``translation_stale``) and release checks.
    """
    result = {}
    for field, values in fields_values.items():
        stale = stale_languages(state, field, values)
        if stale:
            result[field] = stale
    return result


def modeltranslation_values(instance, field, languages) -> dict:
    """``{lang: text}`` for a django-modeltranslation column pair, e.g.
    ``modeltranslation_values(page, "title", ("de", "en"))`` reads
    ``page.title_de`` / ``page.title_en``."""
    return {lang: getattr(instance, f"{field}_{lang}", "") for lang in languages}
