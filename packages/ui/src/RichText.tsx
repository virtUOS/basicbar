// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** Renders server-sanitized rich HTML (an allowlist such as
 * `basicbar_integrations.html_sanitize.clean_html`). The backend is the
 * security boundary: every rich field is cleaned on save/import, so the
 * stored HTML is safe to inject here. Pairs with `RichTextEditor`. */

/** The default prose styling of `RichText`. Exported so a call site can build
 *  on it (`className={\`${richTextClass} mt-4\`}`) instead of copying it. */
export const richTextClass =
  "text-slate-700 dark:text-slate-300 [&_img]:max-w-full [&_img]:h-auto [&_p]:my-2 " +
  "[&_ul]:list-disc [&_ul]:pl-6 [&_ol]:list-decimal [&_ol]:pl-6 [&_li]:my-0.5 " +
  "[&_h2]:mt-4 [&_h2]:mb-1 [&_h2]:text-xl [&_h2]:font-bold [&_h2]:text-slate-900 dark:[&_h2]:text-slate-100 " +
  "[&_h3]:mt-3 [&_h3]:mb-1 [&_h3]:text-base [&_h3]:font-semibold [&_h3]:text-slate-900 dark:[&_h3]:text-slate-100 " +
  "[&_a]:font-medium [&_a]:text-brand-700 [&_a]:underline dark:[&_a]:text-brand-300 " +
  "[&_strong]:font-semibold [&_em]:italic";

export interface RichTextProps {
  html: string;
  /** Fully REPLACES the default styling (`richTextClass`) — it is not
   *  appended — so a migrated call site can render byte-identically to its
   *  previous markup; some sites use large-display classes (text-3xl,
   *  [&_img]:max-h-64, [&_ul]:pl-8) that would clash with the prose default.
   *  To extend the default instead, compose it: `${richTextClass} mt-4`. */
  className?: string;
}

export function RichText({ html, className }: RichTextProps) {
  return (
    <div className={className ?? richTextClass} dangerouslySetInnerHTML={{ __html: html }} />
  );
}
