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
import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode } from "react";
import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";
import i18n, { SUPPORTED_LANGUAGES } from "./i18n";
import {
  defaultContentLangLabel,
  getDefaultContentLang,
  isTranslationEnabled,
} from "./contentLang";
import {
  MAX_TRANSLATE_LENGTH,
  useTranslationForm,
  type TranslatableEntry,
  type TranslateFormat,
} from "./TranslationForm";

/** Language tabs ordered with the current UI language first, so the primary
 *  entry happens in the editor's own language. */
function orderedLangs(): { code: string; label: string }[] {
  const ui = (i18n.resolvedLanguage ?? "en").split("-")[0];
  const langs = SUPPORTED_LANGUAGES.map((l) => ({ code: l.code, label: l.label }));
  return [...langs].sort((a, b) => {
    if (a.code === ui) return -1;
    if (b.code === ui) return 1;
    return 0;
  });
}

function stripHtml(html: string): string {
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.textContent?.trim() ?? "";
}

export interface RenderInputArgs {
  lang: string;
  value: string;
  onChange: (value: string) => void;
  id: string;
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
  /** Fires when the active-language input loses focus (e.g. onBlur-save);
   *  not wired for `renderInput` editors. */
  onBlur?: () => void;
  /** Fires with the currently-edited language on mount and on every tab
   *  switch — lets a parent-rendered live preview follow the tab. */
  onActiveLangChange?: (lang: string) => void;
  /** Single-language authoring (e.g. an "easy mode"): no tabs, no translate
   *  button, no "translate all" registration; edits the canonical language. */
  singleLanguage?: boolean;
  /** "html" marks values as rich HTML: status dots ignore markup and the
   *  translate call preserves it (`format=html`). */
  format?: TranslateFormat;
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
  renderInput,
}: TranslatableFieldProps) {
  const { t } = useTranslation();
  const defaultLang = getDefaultContentLang();
  const langs = orderedLangs();
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

  /** Filled-state per language; rich HTML counts markup-only as empty. */
  const plainOf = (lang: string) => {
    const text = values[lang] ?? "";
    return format === "html" ? stripHtml(text) : text.trim();
  };

  // Register with the form-wide "translate all" controller (if present) and
  // keep a live snapshot it can read/write. Follow the language it switches to.
  const form = useTranslationForm();
  const holder = useRef<TranslatableEntry>({ values, onChange, format });
  holder.current = { values, onChange, format };
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

  const canonicalEmpty = required && !plainOf(defaultLang);

  // Offer machine-translation pre-fill for the language currently shown when
  // it is empty. Prefer the default/canonical language as the source;
  // otherwise translate from whichever other language already has text — so
  // the missing language is filled regardless of which one was entered first.
  const sourceLang = plainOf(defaultLang)
    ? defaultLang
    : langs.find((l) => l.code !== active && plainOf(l.code))?.code;
  const source = sourceLang ? (values[sourceLang] ?? "").trim() : "";
  const sourceLabel =
    langs.find((l) => l.code === sourceLang)?.label ?? sourceLang ?? "";
  const [translating, setTranslating] = useState(false);
  const [translateError, setTranslateError] = useState<string | null>(null);
  const canTranslate =
    !singleLanguage &&
    !!form &&
    isTranslationEnabled() &&
    !plainOf(active) &&
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

  return (
    <div className={`block text-xs text-slate-500 dark:text-slate-400 ${className}`}>
      {(label || showTabs) && (
        <div className="flex items-center justify-between gap-2">
          {label ? (
            <span className="flex items-center gap-1">
              <label htmlFor={inputId} className={labelClassName}>
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
                const filled = !!plainOf(lang.code);
                const isActive = lang.code === active;
                // A filled language gets a solid dot; an empty one a hollow dot,
                // so you can tell at a glance whether the language you're *not*
                // viewing has text. A missing required default language turns
                // amber.
                const missingRequired =
                  !filled && required && lang.code === defaultLang;
                const dotClass = filled
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
                    title={`${lang.label} — ${
                      filled ? t("translated") : t("not translated")
                    }`}
                  >
                    <span
                      aria-hidden="true"
                      className={`inline-block h-1.5 w-1.5 rounded-full border ${dotClass}`}
                    />
                    {lang.code}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}
      <div className="mt-1">
        {renderInput ? (
          renderInput({ lang: active, value, onChange: set, id: inputId })
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
      {canTranslate && (
        <button
          type="button"
          onClick={() => void prefillTranslation()}
          disabled={translating}
          className="mt-1.5 inline-flex items-center gap-1.5 rounded-full border border-brand-300 bg-brand-50 px-3 py-1 text-xs font-semibold text-brand-700 transition-colors hover:bg-brand-100 disabled:opacity-50 dark:border-brand-400/40 dark:bg-brand-400/10 dark:text-brand-200 dark:hover:bg-brand-400/20"
        >
          <Languages className="h-3.5 w-3.5" aria-hidden="true" />
          {translating
            ? t("Translating…")
            : t("Translate from {{language}}", { language: sourceLabel })}
        </button>
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
