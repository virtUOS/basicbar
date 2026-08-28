// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** "Translate all fields" for the authoring editors: a context every mounted
 * TranslatableField registers itself with, plus a floating button that fills
 * the empty translations across the open editor in one pass and switches the
 * fields to the translated language for review. Never overwrites an existing
 * translation. The actual HTTP call is injected by the tool (`translate`
 * prop), so the package stays free of any API client. */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";
import type { MutableRefObject, ReactNode } from "react";
import { Languages } from "lucide-react";
import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "./i18n";
import { getDefaultContentLang, isTranslationEnabled } from "./contentLang";

export type TranslateFormat = "text" | "html";

/** Machine-translate `text`; resolves to the translated text. Tools wire this
 *  to their `/api/translate/` client (basicbar-integrations contract). */
export type TranslateFn = (
  text: string,
  source: string,
  target: string,
  format: TranslateFormat,
) => Promise<string>;

/** Live snapshot a TranslatableField exposes so "translate all" can read its
 * current per-language values and write the translation back into the right
 * language. `format` selects the translate format (rich text → HTML). */
export interface TranslatableEntry {
  values: Record<string, string | null | undefined>;
  onChange: (lang: string, value: string) => void;
  format: TranslateFormat;
  /** Called after a machine translation was written via ``onChange`` — the
   *  moment the languages are known-synchronous. Tools persist their
   *  translation-sync state here (see basicbar_integrations.translation_sync). */
  onTranslated?: (lang: string, value: string) => void;
}

interface TranslationFormState {
  register: (id: string, holder: MutableRefObject<TranslatableEntry>) => void;
  unregister: (id: string) => void;
  /** Language every field should switch to after a bulk translation. */
  forced: { lang: string | null; nonce: number };
  translate: TranslateFn;
}

const TranslationFormContext = createContext<TranslationFormState | undefined>(
  undefined,
);

export function useTranslationForm(): TranslationFormState | undefined {
  return useContext(TranslationFormContext);
}

/** Cap on the text sent per translate call — the endpoint has no length guard,
 *  so the editor bounds it here to avoid unbounded upstream provider calls. */
export const MAX_TRANSLATE_LENGTH = 5000;

/** Wraps the app so every mounted TranslatableField registers itself; renders a
 * floating "translate all fields" button that fills empty translations across
 * the open editor and switches the fields to the translated language. */
export function TranslationFormProvider({
  children,
  translate,
}: {
  children: ReactNode;
  translate: TranslateFn;
}) {
  const { t } = useTranslation();
  const registry = useRef(
    new Map<string, MutableRefObject<TranslatableEntry>>(),
  );
  const [count, setCount] = useState(0); // # registered fields (button visibility)
  const [forced, setForced] = useState<{ lang: string | null; nonce: number }>({
    lang: null,
    nonce: 0,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Stable identities so registered fields don't re-register on every provider
  // state change (count/forced/busy/error).
  const register = useCallback(
    (id: string, holder: MutableRefObject<TranslatableEntry>) => {
      registry.current.set(id, holder);
      setCount(registry.current.size);
    },
    [],
  );
  const unregister = useCallback((id: string) => {
    registry.current.delete(id);
    setCount(registry.current.size);
  }, []);

  const defaultLang = getDefaultContentLang();
  const targets = SUPPORTED_LANGUAGES.map((l) => l.code).filter(
    (c) => c !== defaultLang,
  );

  async function translateAll() {
    setBusy(true);
    setError(null);
    let failures = 0;
    let filled: string | null = null;
    for (const holder of registry.current.values()) {
      for (const lang of targets) {
        // Re-read the live snapshot per target so a value written by an earlier
        // target in this pass is visible (matters with 3+ languages).
        const { values, onChange, format, onTranslated } = holder.current;
        if ((values[lang] ?? "").trim()) continue; // never overwrite
        // Prefer the canonical language as source, else any filled language.
        const sourceLang = (values[defaultLang] ?? "").trim()
          ? defaultLang
          : Object.keys(values).find(
              (l) => l !== lang && (values[l] ?? "").trim(),
            );
        if (!sourceLang) continue;
        try {
          const translated = await translate(
            (values[sourceLang] ?? "").trim().slice(0, MAX_TRANSLATE_LENGTH),
            sourceLang,
            lang,
            format,
          );
          onChange(lang, translated);
          onTranslated?.(lang, translated);
          filled = filled ?? lang;
        } catch {
          failures += 1;
        }
      }
    }
    if (failures) {
      setError(t("Some fields could not be translated."));
    }
    // Switch every field to the language we just filled so the user reviews it.
    if (filled) setForced((f) => ({ lang: filled, nonce: f.nonce + 1 }));
    setBusy(false);
  }

  /** Switch every mounted field to `lang` in one click (no translation), so a
   *  whole record can be filled/reviewed in one language at a time. */
  const forceLang = (lang: string) =>
    setForced((f) => ({ lang, nonce: f.nonce + 1 }));

  // The floating control is useful whenever there are multilingual fields on
  // screen — the language switcher needs no translation backend; only the
  // "translate all" button is gated on it.
  const showControls = count > 0 && SUPPORTED_LANGUAGES.length > 1;
  const showTranslate = isTranslationEnabled() && targets.length > 0;

  const contextValue = useMemo(
    () => ({ register, unregister, forced, translate }),
    [register, unregister, forced, translate],
  );

  return (
    <TranslationFormContext.Provider value={contextValue}>
      {children}
      {showControls && (
        <div className="fixed bottom-6 right-6 z-40 flex flex-col items-end gap-1">
          {error && (
            <span className="rounded-md bg-white px-2 py-1 text-xs text-rose-600 shadow dark:bg-slate-800 dark:text-rose-400">
              {error}
            </span>
          )}
          {/* One combined control: the per-language switch and, if machine
              translation is available, the "translate all" action share a
              single pill so the corner stays uncluttered. */}
          <div className="flex items-center gap-1 rounded-full border border-slate-200 bg-white/90 p-1 text-xs font-semibold shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-800/90">
            <div role="group" aria-label={t("Show all fields in one language")} className="flex items-center gap-1">
              <Languages aria-hidden="true" className="ml-1 h-4 w-4 text-slate-400" />
              {SUPPORTED_LANGUAGES.map((l) => {
                const active = forced.lang === l.code;
                return (
                  <button
                    key={l.code}
                    type="button"
                    onClick={() => forceLang(l.code)}
                    aria-pressed={active}
                    title={t("Show all fields in {{language}}", { language: l.label })}
                    className={`rounded-full px-2.5 py-1 uppercase transition-colors ${
                      active
                        ? "bg-brand-400 text-slate-900"
                        : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-700"
                    }`}
                  >
                    {l.code}
                  </button>
                );
              })}
            </div>
            {showTranslate && (
              <>
                <span aria-hidden="true" className="mx-0.5 h-5 w-px bg-slate-200 dark:bg-slate-600" />
                <button
                  type="button"
                  onClick={() => void translateAll()}
                  disabled={busy}
                  className="inline-flex items-center gap-1.5 rounded-full bg-brand-400 px-3 py-1.5 font-bold text-slate-900 transition-colors hover:bg-brand-500 disabled:opacity-50"
                >
                  <Languages className="h-4 w-4" aria-hidden="true" />
                  {busy ? t("Translating…") : t("Translate all fields")}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </TranslationFormContext.Provider>
  );
}
