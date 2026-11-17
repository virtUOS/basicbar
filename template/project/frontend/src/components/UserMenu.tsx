// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** Account menu of the signed-in user, built like the sibling -bar tools
 *  (convention: "Kopfzeile: Anmelden und Kontomenü" in the @basicbar/ui README):
 *  avatar button → identity, tool items, language, appearance, sign out. */
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { AppearanceControl, LanguageOptions } from "@basicbar/ui";
import { api, logoutUrl, type Whoami } from "../api";

const separator = <div role="separator" className="my-1 border-t border-slate-100 dark:border-slate-800" />;
const itemClass =
  "block w-full px-3 py-2.5 text-left text-sm text-slate-700 hover:bg-slate-50 dark:text-slate-200 dark:hover:bg-slate-800";

export function UserMenu({ whoami }: { whoami: Whoami }) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // WAI-ARIA menu button: opening focuses the first row, Up/Down cycle, Home/End jump,
  // Escape closes and returns focus to the button, a click outside closes.
  useEffect(() => {
    if (open) menuRef.current?.querySelector<HTMLElement>('[role^="menuitem"]')?.focus();
  }, [open]);
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);
  function onMenuKeyDown(e: React.KeyboardEvent) {
    const rows = Array.from(menuRef.current?.querySelectorAll<HTMLElement>('[role^="menuitem"]') ?? []);
    const i = rows.indexOf(document.activeElement as HTMLElement);
    const next =
      e.key === "ArrowDown" ? (i + 1) % rows.length
      : e.key === "ArrowUp" ? (i - 1 + rows.length) % rows.length
      : e.key === "Home" ? 0
      : e.key === "End" ? rows.length - 1
      : null;
    if (next !== null) {
      e.preventDefault();
      rows[next]?.focus();
    }
  }

  const displayName = [whoami.first_name, whoami.last_name].filter(Boolean).join(" ") || whoami.username || "?";

  return (
    <div className="relative" ref={ref}>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("User menu")}
        className="flex items-center rounded-full p-1 transition-colors duration-150 hover:bg-slate-100 dark:hover:bg-slate-800"
      >
        <span className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-400 text-sm font-bold text-slate-900">
          {displayName[0].toUpperCase()}
        </span>
      </button>
      {open && (
        <div
          ref={menuRef}
          role="menu"
          onKeyDown={onMenuKeyDown}
          // Phones: the header may wrap, so span the viewport instead of hanging off the button.
          className="absolute right-0 z-30 mt-2 w-56 overflow-hidden rounded-xl border border-slate-200 bg-white py-1 shadow-lg shadow-slate-900/5 max-sm:fixed max-sm:left-4 max-sm:right-4 max-sm:w-auto dark:border-slate-700 dark:bg-slate-900"
        >
          <div className="px-3 py-2 text-xs text-slate-500 dark:text-slate-300">
            <p className="truncate">
              {t("Signed in as")}{" "}
              <span className="font-medium text-slate-700 dark:text-slate-200">{displayName}</span>
            </p>
            {whoami.is_staff && (
              <span className="mt-1 inline-block rounded bg-brand-100 px-1.5 py-0.5 text-[10px] font-semibold text-brand-800 dark:bg-brand-900 dark:text-brand-200">
                {t("Admin")}
              </span>
            )}
          </div>
          {/* Tool items (own settings, "My …" pages) go here, each with role="menuitem"
              and itemClass, followed by one separator. */}
          {separator}
          <LanguageOptions onChange={(lang) => void api.setLanguage(lang).catch(() => {})} />
          {separator}
          <AppearanceControl />
          {separator}
          <a href={logoutUrl} role="menuitem" className={itemClass}>
            {t("Sign out")}
          </a>
        </div>
      )}
    </div>
  );
}
