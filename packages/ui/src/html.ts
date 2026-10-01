// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** Small helpers for the HTML that rich-text fields store. They parse via the
 * DOM (not a regex), so entities and nested markup are handled like the
 * browser handles them; nothing is executed — `innerHTML` on a detached
 * element never runs scripts or loads resources synchronously. */

/** The visible text of an HTML fragment, whitespace-trimmed. */
export function stripHtml(html: string): string {
  if (!html) return "";
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.textContent?.trim() ?? "";
}

/** True when a stored rich-text value carries no content: no visible text and
 * no image. An editor that was opened and closed again leaves `<p></p>`
 * behind — that is empty; an image-only caption is not. */
export function isEmptyHtml(html: string | null | undefined): boolean {
  if (!html) return true;
  if (stripHtml(html)) return false;
  return !/<img[\s>]/i.test(html);
}
