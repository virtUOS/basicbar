// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** Shared preference controls for the -bar tools: language and appearance,
 * either as rows inside the app's own account menu (`LanguageOptions` +
 * `AppearanceControl`) or, for signed-out visitors, as a round popover
 * button (`PreferencesMenu`). */
import { Check, Monitor, Moon, SlidersHorizontal, Sun } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { SUPPORTED_LANGUAGES } from "./i18n";
import { useTheme, type Appearance } from "./theme";

/** Auto / Light / Dark setting. Auto follows the OS; an explicit pick
 *  overrides it. Full-width radio rows (icon + label + check on the active
 *  option) to match the menu vocabulary. */
export function AppearanceControl() {
  const { t } = useTranslation();
  const { appearance, setAppearance } = useTheme();
  const options: {
    value: Appearance;
    label: string;
    hint?: string;
    icon: typeof Sun;
  }[] = [
    { value: "auto", label: t("Auto"), hint: t("(follows your system)"), icon: Monitor },
    { value: "light", label: t("Light"), icon: Sun },
    { value: "dark", label: t("Dark"), icon: Moon },
  ];
  return (
    <div role="radiogroup" aria-label={t("Appearance")}>
      <p className="px-3 pb-0.5 pt-1 text-xs text-slate-400 dark:text-slate-300">
        {t("Appearance")}
      </p>
      {options.map((opt) => {
        const active = appearance === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => setAppearance(opt.value)}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
          >
            <opt.icon aria-hidden className="h-4 w-4 text-slate-400" />
            <span className="flex-1">
              {opt.label}
              {opt.hint && (
                <span className="block text-xs text-slate-400 dark:text-slate-300">
                  {opt.hint}
                </span>
              )}
            </span>
            {active && <Check aria-hidden className="h-4 w-4 text-brand-600" />}
          </button>
        );
      })}
    </div>
  );
}

/** Language options as `menuitemradio` rows. There is deliberately no "Auto"
 *  entry: without a manual pick the detector follows the system and the
 *  resolved language is the one marked; a pick is cached by i18next (the
 *  detector's cache) and is therefore binding from then on. `onChange` lets
 *  the app persist the choice server-side; `onPicked` lets a menu close. */
export function LanguageOptions({
  onChange,
  onPicked,
}: {
  onChange?: (lang: string) => void;
  onPicked?: () => void;
}) {
  const { i18n } = useTranslation();
  const resolved = i18n.resolvedLanguage ?? i18n.language;
  const current = SUPPORTED_LANGUAGES.some((l) => l.code === resolved)
    ? resolved
    : SUPPORTED_LANGUAGES[0]?.code;
  return (
    <>
      {SUPPORTED_LANGUAGES.map((lang) => (
        <button
          key={lang.code}
          type="button"
          role="menuitemradio"
          aria-checked={lang.code === current}
          onClick={() => {
            i18n.changeLanguage(lang.code);
            onChange?.(lang.code);
            onPicked?.();
          }}
          className="flex w-full items-center justify-between px-3 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-700"
        >
          {lang.label}
          {lang.code === current && (
            <Check aria-hidden className="h-4 w-4 text-brand-600" />
          )}
        </button>
      ))}
    </>
  );
}

/** Round "preferences" button with a popover holding language + appearance —
 *  for signed-out visitors (signed-in users get the same rows in their
 *  account menu). */
export function PreferencesMenu({
  onLanguageChange,
}: {
  onLanguageChange?: (lang: string) => void;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  function closeAndFocus() {
    setOpen(false);
    triggerRef.current?.focus();
  }

  return (
    <div className="relative" ref={ref}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("Preferences")}
        className="flex h-9 w-9 items-center justify-center rounded-full sm:h-10 sm:w-10 text-slate-600 transition-colors duration-150 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-slate-100"
      >
        <SlidersHorizontal aria-hidden className="h-5 w-5" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 z-30 mt-2 w-56 animate-fade-up overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg shadow-slate-900/5 dark:border-slate-700 dark:bg-slate-800"
        >
          <p className="px-3 pb-0.5 pt-1 text-xs text-slate-400 dark:text-slate-300">
            {t("Language")}
          </p>
          <LanguageOptions onChange={onLanguageChange} onPicked={closeAndFocus} />
          <div className="my-1 border-t border-slate-100 dark:border-slate-700" />
          <AppearanceControl />
        </div>
      )}
    </div>
  );
}
