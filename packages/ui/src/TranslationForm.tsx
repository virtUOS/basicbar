// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** "Translate all fields" for the authoring editors: a context every mounted
 * TranslatableField registers itself with, plus a floating button that fills
 * the empty translations across the open editor in one pass and switches the
 * fields to the translated language for review. Never overwrites an existing
 * translation. The actual HTTP call is injected by the tool (`translate`
 * prop), so the package stays free of any API client.
 *
 * The floating controls carry a drag handle (pointer or arrow keys) so they
 * can be moved out of the way; the offset is persisted per browser. A page can
 * instead dock them into its flow with `<TranslationControlsSlot />` — on
 * narrow screens by default, where a floating pill would cover the form. */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type {
  KeyboardEvent as ReactKeyboardEvent,
  MutableRefObject,
  PointerEvent as ReactPointerEvent,
  ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { GripVertical, Languages } from "lucide-react";
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

// ---------------------------------------------------------------------------
// Docking slot

/** Default `media` of `TranslationControlsSlot`: below Tailwind's `md`. */
export const TRANSLATION_SLOT_MEDIA = "(max-width: 767px)";

interface SlotRecord {
  id: number;
  el: HTMLElement;
  matches: boolean;
}

interface SlotRegistry {
  upsert: (slot: SlotRecord) => void;
  remove: (id: number) => void;
}

const SlotContext = createContext<SlotRegistry | undefined>(undefined);
let nextSlotId = 0;

/** Placeholder where a page wants the translation controls to sit in the
 * flow (e.g. at the top of a form). While it is mounted and `media` matches
 * (default: below Tailwind `md`), the nearest `TranslationFormProvider`
 * renders its controls in here instead of floating over the page. Empty —
 * and hidden via `:empty` — otherwise. With several mounted slots, the most
 * recently mounted one wins. */
export function TranslationControlsSlot({
  className = "",
  media = TRANSLATION_SLOT_MEDIA,
}: {
  className?: string;
  /** Media query under which the controls dock here. */
  media?: string;
}) {
  const registry = useContext(SlotContext);
  const ref = useRef<HTMLDivElement>(null);
  const idRef = useRef<number | null>(null);
  if (idRef.current === null) idRef.current = ++nextSlotId;

  // Unregister only on unmount (or provider change): a changed `media` must
  // update the slot in place, not re-append it as "most recently mounted".
  useLayoutEffect(() => {
    if (!registry) return;
    const id = idRef.current!;
    return () => registry.remove(id);
  }, [registry]);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!registry || !el) return;
    const id = idRef.current!;
    const mql =
      typeof window.matchMedia === "function" ? window.matchMedia(media) : null;
    const report = () => registry.upsert({ id, el, matches: !!mql?.matches });
    report();
    mql?.addEventListener("change", report);
    return () => mql?.removeEventListener("change", report);
  }, [registry, media]);

  return <div ref={ref} className={`empty:hidden ${className}`.trim()} />;
}

// ---------------------------------------------------------------------------
// Movable floating controls

type Offset = { x: number; y: number };
const ZERO: Offset = { x: 0, y: 0 };
const OFFSET_KEY = "basicbar_translation_controls_offset";
/** Gap kept between the dragged controls and the viewport edge. */
const EDGE = 4;

function loadOffset(): Offset {
  try {
    const raw = localStorage.getItem(OFFSET_KEY);
    if (!raw) return ZERO;
    const v = JSON.parse(raw) as Partial<Offset>;
    if (typeof v?.x === "number" && typeof v?.y === "number"
        && Number.isFinite(v.x) && Number.isFinite(v.y)) {
      return { x: v.x, y: v.y };
    }
  } catch {
    // storage blocked or garbage — fall back to the anchor position
  }
  return ZERO;
}

function saveOffset(o: Offset) {
  try {
    if (o.x === 0 && o.y === 0) localStorage.removeItem(OFFSET_KEY);
    else localStorage.setItem(OFFSET_KEY, JSON.stringify(o));
  } catch {
    // not persisted — the move still applies for this page view
  }
}

/** Clamp `next` so the element (whose untranslated box is `base`) stays
 * fully inside the viewport. */
function clampOffset(next: Offset, base: DOMRect): Offset {
  const vw = document.documentElement.clientWidth || window.innerWidth;
  const vh = document.documentElement.clientHeight || window.innerHeight;
  const clamp = (v: number, lo: number, hi: number) =>
    hi < lo ? lo : Math.min(Math.max(v, lo), hi);
  return {
    x: Math.round(clamp(next.x, EDGE - base.left, vw - EDGE - base.right)),
    y: Math.round(clamp(next.y, EDGE - base.top, vh - EDGE - base.bottom)),
  };
}

/** The element's box without the current translate offset. */
function baseRect(el: HTMLElement, current: Offset): DOMRect {
  const r = el.getBoundingClientRect();
  return new DOMRect(r.left - current.x, r.top - current.y, r.width, r.height);
}

/** Wraps the app so every mounted TranslatableField registers itself; renders a
 * floating "translate all fields" button that fills empty translations across
 * the open editor and switches the fields to the translated language. */
export function TranslationFormProvider({
  children,
  translate,
  controlsClassName = "fixed bottom-6 right-6 z-40",
  slotControlsClassName = "flex justify-end",
  movable = true,
}: {
  children: ReactNode;
  translate: TranslateFn;
  /** Positioning of the floating controls (replaces the default
   *  `fixed bottom-6 right-6 z-40`) — e.g. to lift them above a tool's own
   *  sticky action bar on narrow screens: `fixed bottom-6 right-6 z-40
   *  max-md:bottom-[5.5rem]`. The pill's own layout is not affected. This is
   *  the anchor; a drag offset is applied on top of it. */
  controlsClassName?: string;
  /** Classes of the controls when docked into a `TranslationControlsSlot`
   *  (replaces the default `flex justify-end`, i.e. right-aligned). */
  slotControlsClassName?: string;
  /** Show the drag handle on the floating controls (default `true`). It only
   *  appears while the controls are `position: fixed`/`absolute`. */
  movable?: boolean;
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
  const targets = useMemo(
    () => SUPPORTED_LANGUAGES.map((l) => l.code).filter((c) => c !== defaultLang),
    [defaultLang],
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

  // --- docking slots ------------------------------------------------------
  const [slots, setSlots] = useState<SlotRecord[]>([]);
  const slotRegistry = useMemo<SlotRegistry>(
    () => ({
      upsert: (slot) =>
        setSlots((prev) => {
          const i = prev.findIndex((s) => s.id === slot.id);
          if (i === -1) return [...prev, slot];
          const old = prev[i];
          if (old.el === slot.el && old.matches === slot.matches) return prev;
          const copy = prev.slice();
          copy[i] = slot;
          return copy;
        }),
      remove: (id) => setSlots((prev) => prev.filter((s) => s.id !== id)),
    }),
    [],
  );
  // Most recently mounted slot wins (mount order = registration order).
  const latestSlot = slots.length ? slots[slots.length - 1] : undefined;
  const dockTarget = latestSlot?.matches ? latestSlot.el : null;

  // --- movable floating controls -----------------------------------------
  const floatRef = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState<Offset>(loadOffset);
  const offsetRef = useRef(offset);
  offsetRef.current = offset;
  // The handle only makes sense while the tool positions the controls out of
  // the flow (a translate on an in-flow element would just overlap content).
  const [positioned, setPositioned] = useState(false);
  const floating = showControls && !dockTarget;
  const canMove = movable && floating && positioned;

  useLayoutEffect(() => {
    if (!floating) return;
    const sync = () => {
      const el = floatRef.current;
      if (!el) return;
      const pos = window.getComputedStyle(el).position;
      const isOut = pos === "fixed" || pos === "absolute";
      setPositioned(isOut);
      // Until `positioned` is set no offset is applied yet, so the box below
      // would be off by it; this effect re-runs once it flips.
      if (!isOut || !movable || !positioned) return;
      // Re-clamp (after a resize, a size change of the pill itself — error
      // message, "Translating…" — or with an offset stored on a wider
      // screen) without persisting, so a wider window restores the spot.
      const cur = offsetRef.current;
      const next = clampOffset(cur, baseRect(el, cur));
      if (next.x !== cur.x || next.y !== cur.y) {
        offsetRef.current = next;
        setOffset(next);
      }
    };
    sync();
    window.addEventListener("resize", sync);
    const ro =
      typeof ResizeObserver !== "undefined" && floatRef.current
        ? new ResizeObserver(() => sync())
        : null;
    if (ro && floatRef.current) ro.observe(floatRef.current);
    return () => {
      window.removeEventListener("resize", sync);
      ro?.disconnect();
    };
  }, [floating, movable, positioned, controlsClassName]);

  const drag = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    start: Offset;
    base: DOMRect;
  } | null>(null);

  const moveTo = (next: Offset, persist: boolean) => {
    const el = floatRef.current;
    if (!el) return;
    const clamped = clampOffset(next, baseRect(el, offsetRef.current));
    offsetRef.current = clamped;
    setOffset(clamped);
    if (persist) saveOffset(clamped);
  };
  const resetOffset = () => {
    offsetRef.current = ZERO;
    setOffset(ZERO);
    saveOffset(ZERO);
  };

  const onHandlePointerDown = (e: ReactPointerEvent<HTMLButtonElement>) => {
    if (e.button !== 0 || !floatRef.current) return;
    e.preventDefault(); // no text selection / focus scroll while dragging
    e.currentTarget.setPointerCapture(e.pointerId);
    drag.current = {
      pointerId: e.pointerId,
      startX: e.clientX,
      startY: e.clientY,
      start: offsetRef.current,
      base: baseRect(floatRef.current, offsetRef.current),
    };
  };
  const onHandlePointerMove = (e: ReactPointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    if (!d || d.pointerId !== e.pointerId) return;
    const next = clampOffset(
      { x: d.start.x + e.clientX - d.startX, y: d.start.y + e.clientY - d.startY },
      d.base,
    );
    offsetRef.current = next;
    setOffset(next);
  };
  const endDrag = (e: ReactPointerEvent<HTMLButtonElement>) => {
    const d = drag.current;
    if (!d || d.pointerId !== e.pointerId) return;
    drag.current = null;
    if (e.currentTarget.hasPointerCapture(e.pointerId)) {
      e.currentTarget.releasePointerCapture(e.pointerId);
    }
    const o = offsetRef.current;
    if (o.x !== d.start.x || o.y !== d.start.y) saveOffset(o);
  };
  const onHandleKeyDown = (e: ReactKeyboardEvent<HTMLButtonElement>) => {
    const step = e.shiftKey ? 64 : 16;
    const o = offsetRef.current;
    const moves: Record<string, Offset> = {
      ArrowLeft: { x: o.x - step, y: o.y },
      ArrowRight: { x: o.x + step, y: o.y },
      ArrowUp: { x: o.x, y: o.y - step },
      ArrowDown: { x: o.x, y: o.y + step },
    };
    if (e.key in moves) {
      e.preventDefault();
      moveTo(moves[e.key], true);
    } else if (e.key === "Home" || e.key === "Escape") {
      e.preventDefault();
      // Don't let the reset also close a surrounding dialog.
      e.stopPropagation();
      resetOffset();
    }
  };

  const renderControls = (withHandle: boolean) => (
    <>
      {error && (
        <span className="rounded-md bg-white px-2 py-1 text-xs text-rose-600 shadow dark:bg-slate-800 dark:text-rose-400">
          {error}
        </span>
      )}
      {/* One combined control: the per-language switch and, if machine
          translation is available, the "translate all" action share a
          single pill so the corner stays uncluttered. */}
      <div className="flex items-center gap-1 rounded-full border border-slate-200 bg-white/90 p-1 text-xs font-semibold shadow-lg backdrop-blur dark:border-slate-700 dark:bg-slate-800/90">
        {withHandle && (
          <button
            type="button"
            aria-label={t("Move translation controls")}
            title={t("Move translation controls")}
            onPointerDown={onHandlePointerDown}
            onPointerMove={onHandlePointerMove}
            onPointerUp={endDrag}
            onPointerCancel={endDrag}
            onDoubleClick={resetOffset}
            onKeyDown={onHandleKeyDown}
            className="cursor-grab touch-none rounded-full p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 active:cursor-grabbing dark:hover:bg-slate-700 dark:hover:text-slate-200"
          >
            <GripVertical aria-hidden="true" className="h-4 w-4" />
          </button>
        )}
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
    </>
  );

  return (
    <TranslationFormContext.Provider value={contextValue}>
      <SlotContext.Provider value={slotRegistry}>
        {children}
      </SlotContext.Provider>
      {showControls &&
        (dockTarget ? (
          createPortal(
            <div className={slotControlsClassName}>
              <div className="flex flex-col items-end gap-1">
                {renderControls(false)}
              </div>
            </div>,
            dockTarget,
          )
        ) : (
          <div
            ref={floatRef}
            className={`${controlsClassName} flex flex-col items-end gap-1`}
            style={
              canMove && (offset.x || offset.y)
                ? // The individual `translate` property composes with any
                  // Tailwind transform utility in `controlsClassName`
                  // (e.g. `-translate-x-1/2`) instead of replacing it.
                  { translate: `${offset.x}px ${offset.y}px` }
                : undefined
            }
          >
            {renderControls(canMove)}
          </div>
        ))}
    </TranslationFormContext.Provider>
  );
}
