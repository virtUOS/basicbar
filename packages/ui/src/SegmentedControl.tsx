// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import {
  useRef,
  useState,
  type CSSProperties,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
} from "react";

export interface SegOption<T extends string> {
  value: T;
  label: ReactNode;
  /** Tooltip; defaults to a string label (see the truncation note below). */
  title?: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Accessible name of the group. */
  ariaLabel: string;
  disabled?: boolean;
  /** "sm" (default): compact, text-xs. "md": 44 px touch targets, text-sm. */
  size?: "sm" | "md";
  className?: string;
}

const DRAG_THRESHOLD = 4; // px of travel before a press becomes a drag

/** Equal-width segmented control with an animated sliding thumb — a choice
 *  of one out of a few, visibly different from toggle/filter pills. Supports
 *  click, keyboard (the segments are real buttons) and pointer-drag: the
 *  thumb follows the finger and snaps to the nearest segment on release. */
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  ariaLabel,
  disabled = false,
  size = "sm",
  className = "",
}: SegmentedControlProps<T>) {
  const n = options.length;
  const activeIndex = Math.max(0, options.findIndex((o) => o.value === value));
  const trackRef = useRef<HTMLDivElement>(null);
  const [dragX, setDragX] = useState<number | null>(null); // thumb px offset while dragging
  // Pointer state. `startX` marks a pressed pointer; `dragging` flips only
  // once it moves past DRAG_THRESHOLD — until then it's a plain press, so we
  // do NOT capture the pointer and let the native click reach the button
  // (capturing eagerly would redirect the click to the track and kill taps).
  const startXRef = useRef<number | null>(null);
  const draggingRef = useRef(false);
  const movedRef = useRef(false);

  function seg() {
    const track = trackRef.current!;
    const inner = track.clientWidth - 4; // p-0.5 = 2px each side
    return { left: track.getBoundingClientRect().left, inner, w: inner / n };
  }
  function thumbLeftFrom(clientX: number) {
    const { left, inner, w } = seg();
    return Math.min(inner - w, Math.max(0, clientX - left - 2 - w / 2));
  }
  function indexFrom(left: number) {
    return Math.min(n - 1, Math.max(0, Math.round(left / seg().w)));
  }

  function onPointerDown(e: ReactPointerEvent<HTMLDivElement>) {
    if (disabled) return;
    startXRef.current = e.clientX;
    draggingRef.current = false;
    movedRef.current = false;
  }
  function onPointerMove(e: ReactPointerEvent<HTMLDivElement>) {
    if (startXRef.current === null) return;
    if (!draggingRef.current) {
      if (Math.abs(e.clientX - startXRef.current) < DRAG_THRESHOLD) return;
      // Real drag begins: now capture the pointer so it keeps tracking even
      // if the finger leaves the control, and suppress the trailing click.
      draggingRef.current = true;
      movedRef.current = true;
      e.currentTarget.setPointerCapture(e.pointerId);
    }
    setDragX(thumbLeftFrom(e.clientX));
  }
  function onPointerUp(e: ReactPointerEvent<HTMLDivElement>) {
    const wasDrag = draggingRef.current;
    startXRef.current = null;
    draggingRef.current = false;
    if (!wasDrag) return; // a plain tap: let the button's onClick handle it
    setDragX(null);
    const picked = options[indexFrom(thumbLeftFrom(e.clientX))].value;
    if (picked !== value) onChange(picked);
  }

  const thumbStyle: CSSProperties = {
    width: `calc((100% - 4px) / ${n})`,
    transform: dragX !== null ? `translateX(${dragX}px)` : `translateX(${activeIndex * 100}%)`,
    transition: dragX !== null ? "none" : undefined,
  };
  const segSize = size === "md" ? "min-h-[44px] px-2 sm:px-4" : "px-1.5 py-1 sm:px-2.5";

  return (
    <div
      ref={trackRef}
      role="radiogroup"
      aria-label={ariaLabel}
      aria-disabled={disabled || undefined}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={() => {
        startXRef.current = null;
        draggingRef.current = false;
        setDragX(null);
      }}
      style={{ touchAction: "none" }}
      className={`relative grid grid-flow-col auto-cols-[minmax(0,1fr)] items-center rounded-full border border-slate-200 p-0.5 dark:border-slate-700 ${
        size === "md" ? "text-sm font-medium" : "text-xs"
      } ${disabled ? "opacity-50" : ""} ${className}`}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute bottom-0.5 left-0.5 top-0.5 rounded-full bg-brand-100 transition-transform duration-150 motion-reduce:transition-none dark:bg-brand-900"
        style={thumbStyle}
      />
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          disabled={disabled}
          onClick={() => {
            if (movedRef.current) {
              movedRef.current = false; // ignore the click synthesized after a drag
              return;
            }
            if (o.value !== value) onChange(o.value);
          }}
          // Too narrow (phones): the label is cut with an ellipsis instead
          // of breaking mid-word; the full text stays in the title.
          title={o.title ?? (typeof o.label === "string" ? o.label : undefined)}
          className={`relative z-10 inline-flex min-w-0 items-center justify-center gap-1.5 rounded-full text-center transition-colors focus-visible:[outline:2px_solid_transparent] focus-visible:[outline-offset:2px] focus-visible:ring-2 focus-visible:ring-brand-500 ${segSize} ${
            o.value === value ? "text-brand-800 dark:text-brand-200" : "text-slate-500 dark:text-slate-400"
          }`}
        >
          {/* Tailwind's preflight makes <svg> display:block, so an icon inside a
              plain block span stacked above its text. A string label keeps the
              ellipsis; a node label (icon + text) is laid out as a flex row. */}
          {typeof o.label === "string" ? (
            <span className="min-w-0 truncate">{o.label}</span>
          ) : (
            <span className="inline-flex min-w-0 items-center justify-center gap-1.5 whitespace-nowrap">
              {o.label}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
