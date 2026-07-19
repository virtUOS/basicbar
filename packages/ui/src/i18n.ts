// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";

/**
 * UI internationalisation. English source strings are used directly as keys
 * (so non-plural English text needs no catalog — the key is the text), with
 * one exception: plurals. i18next selects a plural form by looking up the
 * `_one` / `_other` key variants in the resource, so English needs explicit
 * entries for every pluralized string or it would fall back to the singular
 * key for all counts ("26 product"). `en/translation.json` holds exactly those
 * forms; `de/translation.json` maps each English string to German. The default
 * language comes from the browser; the explicit choice is kept in localStorage.
 *
 * A tool calls `initI18n({ resources })` once at startup (before rendering)
 * with its own catalogs — they live in the tool, the mechanics live here.
 */

export interface Language {
  code: string;
  label: string;
}

const DEFAULT_LANGUAGES: readonly Language[] = [
  { code: "en", label: "English" },
  { code: "de", label: "Deutsch" },
];

/** The languages the running tool supports (set by `initI18n`). */
export let SUPPORTED_LANGUAGES: readonly Language[] = DEFAULT_LANGUAGES;

export function initI18n({
  resources,
  languages = DEFAULT_LANGUAGES,
}: {
  /** Per-language catalogs, e.g. `{ en: {...}, de: {...} }` — the JSON files
   *  live in the tool (`src/locales/<lang>/translation.json`) and can be
   *  handed to a translation service as-is. */
  resources: Record<string, object>;
  languages?: readonly Language[];
}) {
  SUPPORTED_LANGUAGES = languages;
  i18n
    .use(LanguageDetector)
    .use(initReactI18next)
    .init({
      resources: Object.fromEntries(
        Object.entries(resources).map(([lang, catalog]) => [
          lang,
          { translation: catalog },
        ]),
      ),
      fallbackLng: "en",
      supportedLngs: languages.map((l) => l.code),
      nonExplicitSupportedLngs: true, // de-DE, en-GB … → de / en
      interpolation: { escapeValue: false }, // React already escapes
      detection: {
        order: ["localStorage", "navigator"],
        lookupLocalStorage: "lang",
        caches: ["localStorage"],
      },
      // Use the English source string as the lookup key.
      keySeparator: false,
      nsSeparator: false,
      returnEmptyString: false,
    });

  // Keep <html lang> in sync with the active language so screen readers switch
  // pronunciation with the UI (WCAG 3.1.1).
  syncDocumentLang(i18n.resolvedLanguage ?? "en");
  i18n.on("languageChanged", syncDocumentLang);

  return i18n;
}

function syncDocumentLang(lng: string) {
  document.documentElement.lang = lng.split("-")[0];
}

export default i18n;
