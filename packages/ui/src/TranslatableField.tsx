// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** A labelled text field with one tab per content language, per-language
 * "translated / not translated" status dots, and an optional machine-
 * translation pre-fill button (LibreTranslate via the tool's translate
 * endpoint, only when `isTranslationEnabled()`).
 *
 * The value contract is per-language (`values` + `onChange(lang, text)`) —
 * the primitive that serves both storage models of the tools: per-language
 * columns (`title_de`/`title_en`) as well as `{ lang: text }` maps (bridge
 * with `localizedMap`/`setLocalizedLang`). Custom editors (rich text,
 * Markdown, …) plug in via `renderInput`; they stay in the tool. */
import { useEffect, useId, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "./i18n";
import {
  defaultContentLangLabel,
  getDefaultContentLang,
  isTranslationEnabled,
} from "./contentLang";
import { isEmptyHtml } from "./html";
import {
  MAX_TRANSLATE_LENGTH,
  useTranslationForm,
  type TranslatableEntry,
  type TranslateFormat,
} from "./TranslationForm";

/** Language tabs ordered with the current UI language first, so the primary
 *  entry happens in the editor's own language. */
function orderedLangs(uiLang: string): { code: string; label: string }[] {
  const ui = uiLang.split("-")[0];
  const langs = SUPPORTED_LANGUAGES.map((l) => ({ code: l.code, label: l.label }));
  return langs.sort((a, b) => {
    if (a.code === ui) return -1;
    if (b.code === ui) return 1;
    return 0;
  });
}

export interface RenderInputArgs {
  lang: string;
  value: string;
  onChange: (value: string) => void;
  /** The field's `onBlur` prop, passed through so a custom editor can wire
   *  the same blur-save the default input gets. */
  onBlur?: () => void;
  id: string;
  /** Id of the visible `<label>` element, when there is one (omitted for a
   *  labelless/compact field) — pass through as e.g. `aria-labelledby` on a
   *  custom editor that has no native `<label htmlFor>` association of its
   *  own (`RichTextEditor`'s `labelledBy`). */
  labelId?: string;
}

const DEFAULT_INPUT_CLASS =
  "w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-1 focus:ring-brand-600 dark:bg-slate-900 dark:text-slate-100";

export interface TranslatableFieldProps {
  /** Visible label above the field; omit for compact inline uses (the
   *  language tabs still render, right-aligned, without a label). */
  label?: string;
  /** Accessible name for the tab list when there is no visible `label`. */
  ariaLabel?: string;
  /** Per-language values, e.g. `{ de: form.title_de, en: form.title_en }`
   *  or `localizedMap(value)`. */
  values: Record<string, string | null | undefined>;
  onChange: (lang: string, value: string) => void;
  /** Styling for the default input/textarea; defaults to the shared style. */
  inputClass?: string;
  /** Extra classes on the outer wrapper (e.g. to size/flex it inside a row). */
  className?: string;
  /** Classes for the label element (default: inherits the wrapper's meta
   *  style; pass e.g. `text-sm font-medium …` for a prominent form label). */
  labelClassName?: string;
  /** Rendered right after the visible label; ignored without `label`. */
  labelAddon?: ReactNode;
  required?: boolean;
  multiline?: boolean;
  rows?: number;
  placeholder?: string;
  /** Helper text shown under the field (applies to every language). */
  hint?: string;
  /** Fires when the active-language input loses focus (e.g. onBlur-save).
   *  A `renderInput` editor receives it as `args.onBlur` and wires it itself. */
  onBlur?: () => void;
  /** Fires with the currently-edited language on mount and on every tab
   *  switch — lets a parent-rendered live preview follow the tab. */
  onActiveLangChange?: (lang: string) => void;
  /** Single-language authoring (e.g. an "easy mode"): no tabs, no translate
   *  button, no "translate all" registration; edits the canonical language. */
  singleLanguage?: boolean;
  /** "html" marks values as rich HTML: status dots ignore markup (an empty
   *  `<p></p>` counts as empty, an image-only value as filled — see
   *  `isEmptyHtml`) and the translate call preserves it (`format=html`). */
  format?: TranslateFormat;
  /** Languages whose translation is potentially outdated (another language
   *  changed since the last recorded sync — computed by the backend via
   *  ``basicbar_integrations.translation_sync``). Marks the tab dot amber
   *  and offers re-translate / mark-up-to-date on the affected tab. */
  stale?: readonly string[];
  /** "Als aktuell markieren": the author confirms the languages are in sync
   *  (e.g. after an intentional single-language correction). Tools persist
   *  the new sync state. Rendered only when the active language is stale. */
  onMarkSynced?: () => void;
  /** Called after a machine translation was written via ``onChange`` — the
   *  moment the languages are known-synchronous. Tools persist their
   *  translation-sync state here. */
  onTranslated?: (lang: string, text: string) => void;
  /** Custom editor per language (e.g. rich text or Markdown); replaces the
   *  default input. The editor stays in the tool. */
  renderInput?: (args: RenderInputArgs) => ReactNode;
}

export function TranslatableField({
  label,
  ariaLabel,
  values,
  onChange,
  inputClass = DEFAULT_INPUT_CLASS,
  className = "",
  labelClassName = "",
  labelAddon,
  required = false,
  multiline = false,
  rows = 2,
  placeholder,
  hint,
  onBlur,
  onActiveLangChange,
  singleLanguage = false,
  format = "text",
  stale = [],
  onMarkSynced,
  onTranslated,
  renderInput,
}: TranslatableFieldProps) {
  const { t, i18n } = useTranslation();
  const defaultLang = getDefaultContentLang();
  const uiLang = i18n.resolvedLanguage ?? "en";
  const langs = useMemo(() => orderedLangs(uiLang), [uiLang]);
  const [active, setActive] = useState(
    singleLanguage ? defaultLang : (langs[0]?.code ?? defaultLang),
  );
  const baseId = useId();
  const inputId = `${baseId}-${active}`;

  useEffect(() => {
    onActiveLangChange?.(active);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active]);

  const value = values[active] ?? "";
  const set = (v: string) => onChange(active, v);

  // Filled-state per language. For rich HTML this parses the value via the
  // DOM, so it is computed once per render of the values, not once per
  // tab/lookup — a form with many rich fields re-renders on every keystroke.
  const filledByLang = useMemo(() => {
    const out: Record<string, boolean> = {};
    for (const l of SUPPORTED_LANGUAGES) {
      const text = values[l.code] ?? "";
      out[l.code] = format === "html" ? !isEmptyHtml(text) : !!text.trim();
    }
    return out;
  }, [values, format]);
  const filledIn = (lang: string) => filledByLang[lang] ?? false;

  // Register with the form-wide "translate all" controller (if present) and
  // keep a live snapshot it can read/write. Follow the language it switches to.
  const form = useTranslationForm();
  const holder = useRef<TranslatableEntry>({ values, onChange, format, onTranslated });
  holder.current = { values, onChange, format, onTranslated };
  const register = form?.register;
  const unregister = form?.unregister;
  useEffect(() => {
    if (!register || !unregister || singleLanguage) return;
    register(baseId, holder);
    return () => unregister(baseId);
  }, [register, unregister, baseId, singleLanguage]);
  const forcedLang = form?.forced.lang;
  const forcedNonce = form?.forced.nonce;
  useEffect(() => {
    if (forcedLang && !singleLanguage) setActive(forcedLang);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [forcedNonce]);

  const canonicalEmpty = required && !filledIn(defaultLang);

  const activeStale = !singleLanguage && stale.includes(active);

  // Offer machine-translation pre-fill for the language currently shown when
  // it is empty — or when it is stale (then it explicitly re-translates).
  // Prefer the default/canonical language as the source; otherwise translate
  // from whichever other language already has text — so the missing language
  // is filled regardless of which one was entered first.
  const sourceLang =
    defaultLang !== active && filledIn(defaultLang)
      ? defaultLang
      : langs.find((l) => l.code !== active && filledIn(l.code))?.code;
  const source = sourceLang ? (values[sourceLang] ?? "").trim() : "";
  const sourceLabel =
    langs.find((l) => l.code === sourceLang)?.label ?? sourceLang ?? "";
  const [translating, setTranslating] = useState(false);
  const [translateError, setTranslateError] = useState<string | null>(null);
  const canTranslate =
    !singleLanguage &&
    !!form &&
    isTranslationEnabled() &&
    (!filledIn(active) || activeStale) &&
    !!source &&
    sourceLang !== active;

  async function prefillTranslation() {
    if (!form || !sourceLang) return;
    setTranslating(true);
    setTranslateError(null);
    try {
      const translated = await form.translate(
        source.slice(0, MAX_TRANSLATE_LENGTH),
        sourceLang,
        active,
        format,
      );
      onChange(active, translated);
      onTranslated?.(active, translated);
    } catch (err) {
      setTranslateError(
        err instanceof Error ? err.message : t("Translation failed."),
      );
    } finally {
      setTranslating(false);
    }
  }

  const showTabs = !singleLanguage;
  const tabsLabel = ariaLabel ?? label;
  const labelId = label ? `${inputId}-label` : undefined;

  return (
    <div className={`block text-xs text-slate-500 dark:text-slate-400 ${className}`}>
      {(label || showTabs) && (
        <div className="flex items-center justify-between gap-2">
          {label ? (
            <span className="flex items-center gap-1">
              <label id={labelId} htmlFor={inputId} className={labelClassName}>
                {label}
                {required && <span className="text-rose-500"> *</span>}
              </label>
              {labelAddon}
            </span>
          ) : (
            <span />
          )}
          {showTabs && (
            <div className="flex gap-1" role="tablist" aria-label={tabsLabel}>
              {langs.map((lang) => {
                const filled = filledIn(lang.code);
                const isActive = lang.code === active;
                const isStale = stale.includes(lang.code);
                const status =
                  filled && isStale
                    ? t("translation may be outdated")
                    : filled
                      ? t("translated")
                      : t("not translated");
                // A filled language gets a solid dot; an empty one a hollow dot,
                // so you can tell at a glance whether the language you're *not*
                // viewing has text. A missing required default language and a
                // potentially outdated translation turn amber.
                const missingRequired =
                  !filled && required && lang.code === defaultLang;
                const dotClass =
                  filled && isStale
                    ? "bg-amber-500 border-amber-500"
                    : filled
                      ? "bg-emerald-500 border-emerald-500"
                      : missingRequired
                        ? "border-amber-500"
                        : "border-current opacity-40";
                return (
                  <button
                    key={lang.code}
                    type="button"
                    role="tab"
                    aria-selected={isActive}
                    onClick={() => setActive(lang.code)}
                    className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium uppercase transition-colors ${
                      isActive
                        ? "bg-brand-400 text-slate-900"
                        : "bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-400 dark:hover:bg-slate-700"
                    }`}
                    title={`${lang.label} — ${status}`}
                  >
                    <span
                      aria-hidden="true"
                      className={`inline-block h-1.5 w-1.5 rounded-full border ${dotClass}`}
                    />
                    {lang.code}
                    {/* The dot is colour-only; give screen readers the same
                        status the title shows on hover (WCAG 1.4.1). */}
                    <span className="sr-only">
                      {" "}
                      — {status}
                    </span>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
      <div className="mt-1">
        {renderInput ? (
          renderInput({ lang: active, value, onChange: set, onBlur, id: inputId, labelId })
        ) : multiline ? (
          <textarea
            id={inputId}
            rows={rows}
            value={value}
            placeholder={placeholder}
            onChange={(e) => set(e.target.value)}
            onBlur={onBlur}
            className={inputClass}
          />
        ) : (
          <input
            id={inputId}
            value={value}
            placeholder={placeholder}
            onChange={(e) => set(e.target.value)}
            onBlur={onBlur}
            className={inputClass}
          />
        )}
      </div>
      {activeStale && (
        <p className="mt-1 text-amber-600 dark:text-amber-400">
          {t("The other language was changed since this translation.")}
        </p>
      )}
      {(canTranslate || (activeStale && onMarkSynced)) && (
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          {canTranslate && (
            <button
              type="button"
              onClick={() => void prefillTranslation()}
              disabled={translating}
              className="inline-flex items-center gap-1.5 rounded-full border border-brand-300 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 transition-colors hover:bg-brand-100 disabled:opacity-50 dark:border-brand-400/40 dark:bg-brand-400/10 dark:text-brand-200 dark:hover:bg-brand-400/20"
            >
              <Languages className="h-3.5 w-3.5" aria-hidden="true" />
              {translating
                ? t("Translating…")
                : t("Translate from {{language}}", { language: sourceLabel })}
            </button>
          )}
          {activeStale && onMarkSynced && (
            <button
              type="button"
              onClick={onMarkSynced}
              className="inline-flex items-center rounded-full border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-600 transition-colors hover:bg-slate-100 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {t("Mark as up to date")}
            </button>
          )}
        </div>
      )}
      {translateError && <p className="mt-1 text-rose-500">{translateError}</p>}
      {hint && <p className="mt-1 text-slate-400 dark:text-slate-500">{hint}</p>}
      {canonicalEmpty && (
        <p className="mt-1 text-rose-500">
          {t("A value in {{language}} is required.", {
            language: defaultContentLangLabel(),
          })}
        </p>
      )}
    </div>
  );
}
