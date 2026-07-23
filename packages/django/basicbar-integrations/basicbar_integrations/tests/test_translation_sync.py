# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Universität Osnabrück (virtUOS)
from django.test import SimpleTestCase

from basicbar_integrations.translation_sync import (
    changed_languages,
    content_hash,
    modeltranslation_values,
    record_synced,
    stale_languages,
    stale_map,
)


class ContentHashTests(SimpleTestCase):
    def test_none_and_empty_and_whitespace_are_equal(self):
        self.assertEqual(content_hash(None), content_hash(""))
        self.assertEqual(content_hash("  "), content_hash(""))
        self.assertEqual(content_hash("Hallo  "), content_hash("Hallo"))

    def test_different_texts_differ(self):
        self.assertNotEqual(content_hash("Hallo"), content_hash("Hello"))


class SyncStateTests(SimpleTestCase):
    def setUp(self):
        self.values = {"de": "Hallo Welt", "en": "Hello world"}
        self.state = record_synced({}, "title", self.values)

    def test_record_keeps_other_fields(self):
        state = record_synced(self.state, "body", {"de": "x", "en": "y"})
        self.assertIn("title", state)
        self.assertIn("body", state)

    def test_no_baseline_is_never_stale(self):
        self.assertEqual(changed_languages({}, "title", self.values), [])
        self.assertEqual(stale_languages(None, "title", self.values), [])

    def test_unchanged_pair_is_clean(self):
        self.assertEqual(stale_languages(self.state, "title", self.values), [])

    def test_editing_one_language_marks_the_other_stale(self):
        values = {**self.values, "de": "Hallo Welt, neu"}
        self.assertEqual(changed_languages(self.state, "title", values), ["de"])
        self.assertEqual(stale_languages(self.state, "title", values), ["en"])

    def test_editing_both_languages_marks_nothing(self):
        values = {"de": "Neu", "en": "New"}
        self.assertEqual(stale_languages(self.state, "title", values), [])

    def test_empty_counterpart_is_not_stale(self):
        # A language that was empty at sync time and still is has no
        # translation that could age — only the dot for "not translated".
        state = record_synced({}, "title", {"de": "Hallo", "en": ""})
        values = {"de": "Hallo neu", "en": ""}
        self.assertEqual(stale_languages(state, "title", values), [])

    def test_re_recording_clears_staleness(self):
        values = {**self.values, "de": "Hallo Welt, neu"}
        state = record_synced(self.state, "title", values)
        self.assertEqual(stale_languages(state, "title", values), [])

    def test_stale_map_over_fields(self):
        state = record_synced(self.state, "body", {"de": "Text", "en": "Text EN"})
        fields_values = {
            "title": {**self.values, "en": "Hello world, edited"},
            "body": {"de": "Text", "en": "Text EN"},
        }
        self.assertEqual(stale_map(state, fields_values), {"title": ["de"]})


class ModeltranslationValuesTests(SimpleTestCase):
    def test_reads_language_columns(self):
        class Page:
            title_de = "Hallo"
            title_en = "Hello"

        self.assertEqual(
            modeltranslation_values(Page(), "title", ("de", "en")),
            {"de": "Hallo", "en": "Hello"},
        )

    def test_missing_column_is_empty(self):
        class Page:
            title_de = "Hallo"

        self.assertEqual(
            modeltranslation_values(Page(), "title", ("de", "en")),
            {"de": "Hallo", "en": ""},
        )
