// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import { createContext, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

/**
 * Appearance setting: Auto/Light/Dark, Auto = default.
 *
 * - `auto` follows the OS `prefers-color-scheme` and reacts to live changes.
 * - `light` / `dark` are explicit overrides, persisted to localStorage.
 *
 * The actual `.dark` class on <html> is set both here (on change) and by a
 * tiny inline script in index.html that runs before React, so there is no
 * flash of the wrong theme on first paint (see `prePaintScript`).
 */
export type Appearance = "auto" | "light" | "dark";

const DEFAULT_STORAGE_KEY = "appearance";
const DARK_QUERY = "(prefers-color-scheme: dark)";

interface ThemeState {
  appearance: Appearance;
  setAppearance: (next: Appearance) => void;
  /** The effective theme after resolving "auto" against the system. */
  resolved: "light" | "dark";
}

const ThemeContext = createContext<ThemeState | undefined>(undefined);

function readStored(storageKey: string): Appearance {
  try {
    const value = localStorage.getItem(storageKey);
    if (value === "light" || value === "dark" || value === "auto") return value;
  } catch {
    /* private mode / disabled storage — fall back to auto */
  }
  return "auto";
}

function systemPrefersDark(): boolean {
  return window.matchMedia(DARK_QUERY).matches;
}

/** Apply the resolved theme to <html>: the Tailwind `.dark` class plus
 *  `color-scheme` so native controls (scrollbars, date inputs) follow. */
function applyResolved(resolved: "light" | "dark") {
  const root = document.documentElement;
  root.classList.toggle("dark", resolved === "dark");
  root.style.colorScheme = resolved;
}

export function ThemeProvider({
  children,
  storageKey = DEFAULT_STORAGE_KEY,
}: {
  children: ReactNode;
  /** localStorage key for the explicit choice (override to keep an existing
   *  deployment's stored preferences, e.g. abstimmbar's legacy key). */
  storageKey?: string;
}) {
  const [appearance, setAppearanceState] = useState<Appearance>(() =>
    readStored(storageKey),
  );
  const [systemDark, setSystemDark] = useState(systemPrefersDark);

  // React to OS theme changes; only affects the result while in "auto".
  useEffect(() => {
    const mq = window.matchMedia(DARK_QUERY);
    const onChange = (event: MediaQueryListEvent) => setSystemDark(event.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const resolved: "light" | "dark" =
    appearance === "auto" ? (systemDark ? "dark" : "light") : appearance;

  useEffect(() => applyResolved(resolved), [resolved]);

  const setAppearance = (next: Appearance) => {
    setAppearanceState(next);
    try {
      // "auto" is the default, so store it as the absence of a choice — that
      // way the inline pre-paint script falls back to the system preference.
      if (next === "auto") localStorage.removeItem(storageKey);
      else localStorage.setItem(storageKey, next);
    } catch {
      /* ignore storage failures */
    }
  };

  return (
    <ThemeContext.Provider value={{ appearance, setAppearance, resolved }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme(): ThemeState {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}

/** Inline script for index.html, run before React to avoid a flash of the
 *  wrong theme on first paint. Mirrors the ThemeProvider logic — keep in sync.
 *
 *  Usage: `<script>${prePaintScript()}</script>` (same storageKey as the
 *  provider).
 */
export function prePaintScript(storageKey: string = DEFAULT_STORAGE_KEY): string {
  return (
    `(function(){try{var c=localStorage.getItem(${JSON.stringify(storageKey)});` +
    `var d=c==="dark"||(c!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);` +
    `if(d)document.documentElement.classList.add("dark");` +
    `document.documentElement.style.colorScheme=d?"dark":"light";}catch(e){}})();`
  );
}
