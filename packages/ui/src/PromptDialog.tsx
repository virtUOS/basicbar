// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** In-app replacement for the browser's prompt(): a native modal `<dialog>` with one
 * labelled text input, OK and Cancel. `usePromptDialog()` returns the dialog
 * element (render it once, anywhere in the tree) and a Promise-based
 * `prompt()` — `const v = await prompt({ label })` resolves to the entered
 * text, or `null` on Cancel/Esc. Requests are queued (FIFO), so two callers
 * prompting at once (e.g. two uploads finishing back to back) each get their
 * own dialog in turn instead of overwriting each other.
 *
 * Deliberately no `<form>`: the editor usually sits inside the host app's
 * form, where a nested form is invalid and a submit would bubble (React
 * propagates events through the component tree) to the host's handler.
 * Enter is handled on the input instead. */
import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

export interface PromptOptions {
  /** Visible label of the text input (also the dialog's accessible name). */
  label: string;
  /** Prefill of the input (selected on open). Default "". */
  defaultValue?: string;
}

interface PromptRequest extends PromptOptions {
  id: number;
  resolve: (value: string | null) => void;
}

export function usePromptDialog(): {
  dialog: ReactNode;
  prompt: (options: PromptOptions) => Promise<string | null>;
} {
  const { t } = useTranslation();
  const queue = useRef<PromptRequest[]>([]);
  const nextId = useRef(1);
  const [current, setCurrent] = useState<PromptRequest | null>(null);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  // The value to resolve with when the dialog's `close` event fires; every
  // way out (OK, Cancel, Esc, unmount) funnels through that one event.
  const result = useRef<string | null>(null);
  const labelId = useId();
  // prompt() after unmount (e.g. a queued request reaching the front once
  // the editor is gone) must not wait for a dialog that never opens.
  const mounted = useRef(false);

  const prompt = useCallback(
    (options: PromptOptions) =>
      new Promise<string | null>((resolve) => {
        if (!mounted.current) {
          resolve(null);
          return;
        }
        const request = { ...options, id: nextId.current++, resolve };
        queue.current.push(request);
        if (queue.current.length === 1) setCurrent(request);
      }),
    [],
  );

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!current || !dialog) return;
    result.current = null;
    if (!dialog.open) dialog.showModal();
    inputRef.current?.focus();
    inputRef.current?.select();
  }, [current]);

  // Unmount: settle whatever is still pending, so no caller awaits forever.
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      const pending = queue.current;
      queue.current = [];
      pending.forEach((request) => request.resolve(null));
    };
  }, []);

  function finish(value: string | null) {
    result.current = value;
    dialogRef.current?.close(); // → onClose below
  }

  function handleClose() {
    const done = queue.current.shift();
    if (!done) return;
    const value = result.current;
    result.current = null;
    setCurrent(queue.current[0] ?? null);
    done.resolve(value);
  }

  const dialog = (
    <dialog
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby={labelId}
      onClose={handleClose}
      // Esc belongs to this dialog alone: the browser still closes it, but
      // the key must not bubble on to page-level handlers (e.g. a guided
      // tour that ends on Esc).
      onKeyDown={(event) => {
        if (event.key === "Escape") event.stopPropagation();
      }}
      // Esc: the browser closes the dialog itself; `result` is still null,
      // so the close handler resolves null (= cancelled).
      className="m-auto w-[min(28rem,calc(100vw-2rem))] rounded-lg border border-slate-200 bg-white p-4 text-slate-900 shadow-xl backdrop:bg-slate-950/50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-100"
    >
      {current && (
        <div key={current.id} className="grid gap-3">
          <label id={labelId} htmlFor={`${labelId}-input`} className="text-sm font-semibold">
            {current.label}
          </label>
          <input
            ref={inputRef}
            id={`${labelId}-input`}
            type="text"
            defaultValue={current.defaultValue ?? ""}
            onKeyDown={(event) => {
              if (event.key !== "Enter" || event.nativeEvent.isComposing) return;
              event.preventDefault();
              event.stopPropagation();
              finish(event.currentTarget.value);
            }}
            className="w-full rounded border border-field bg-white px-2 py-1.5 text-sm text-slate-900 dark:bg-slate-950 dark:text-slate-100"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => finish(null)}
              className="rounded-full px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
            >
              {t("Cancel")}
            </button>
            <button
              type="button"
              onClick={() => finish(inputRef.current?.value ?? "")}
              className="rounded-full bg-brand-400 px-3 py-1.5 text-sm font-bold text-slate-900 transition-colors hover:bg-brand-500"
            >
              {t("OK")}
            </button>
          </div>
        </div>
      )}
    </dialog>
  );

  return { dialog, prompt };
}
