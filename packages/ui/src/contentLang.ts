// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** Client-side handling of authored, translatable content: fields come back
 * from the backend as `{ lang: text }` maps (or legacy plain strings) and are
 * resolved to the active UI language here. */
import i18n, { SUPPORTED_LANGUAGES } from "./i18n";

/** A translatable value: a `{ lang: text }` map, or a legacy plain string. */
export type LocalizedText = string | Partial<Record<string, string>>;

/** The canonical content language: the one required when authoring content
 * and the first fallback shown. Configured per deployment on the backend
 * (`CONTENT_DEFAULT_LANGUAGE`) and delivered to the SPA via `whoami`; until
 * that resolves we assume German, matching the backend default. */
let defaultContentLang = "de";

export function setDefaultContentLang(lang: string | undefined | null): void {
  if (lang) defaultContentLang = lang;
}

export function getDefaultContentLang(): string {
  return defaultContentLang;
}

/** Whether the backend offers machine-translation pre-fill (LibreTranslate,
 * off by default). */
let translationEnabled = false;

export function setTranslationEnabled(enabled: boolean | undefined | null): void {
  translationEnabled = !!enabled;
}

export function isTranslationEnabled(): boolean {
  return translationEnabled;
}

/** Human-readable label of the default content language (e.g. "Deutsch"). */
export function defaultContentLangLabel(): string {
  return (
    SUPPORTED_LANGUAGES.find((l) => l.code === defaultContentLang)?.label ??
    defaultContentLang.toUpperCase()
  );
}

/** Resolve a translatable text (string or `{ lang: text }` map) to the active
 * UI language, falling back to the default content language, then any
 * non-empty value, then "". A plain string is returned unchanged (legacy /
 * bare fields), so passing one through is always safe. Mirrors the backend's
 * `resolve_translated_text`. */
export function localizedText(value: LocalizedText | null | undefined): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  const ui = (i18n.resolvedLanguage ?? defaultContentLang).split("-")[0];
  return (
    value[ui] ||
    value[defaultContentLang] ||
    Object.values(value).find(Boolean) ||
    ""
  );
}

/** Normalize a translatable value to a `{ lang: text }`-shaped partial map — a
 * bare legacy string becomes the canonical language's entry, `null`/`undefined`
 * becomes `{}`. Lets editors treat every field uniformly as a map while still
 * accepting the legacy shape on load. */
export function localizedMap(
  value: LocalizedText | null | undefined,
): Partial<Record<string, string>> {
  if (value == null) return {};
  if (typeof value === "string") return { [defaultContentLang]: value };
  return value;
}

/** Return a copy of `value` with `lang`'s entry set to `text`, preserving any
 * other language already present (including one implied by a legacy plain
 * string). Used when an editor writes into a single language — e.g. applying
 * an AI rephrasing or translation result — without clobbering the rest. */
export function setLocalizedLang(
  value: LocalizedText | null | undefined,
  lang: string,
  text: string,
): LocalizedText {
  return { ...localizedMap(value), [lang]: text };
}
