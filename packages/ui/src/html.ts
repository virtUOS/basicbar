// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** Small helpers for the HTML that rich-text fields store. They parse via the
 * DOM (not a regex), so entities and nested markup are handled like the
 * browser handles them. Parsing happens in an inert `DOMParser` document:
 * unlike `innerHTML` on an element of the live document — which loads images
 * and runs inline handlers such as `<img onerror=…>` even when detached —
 * nothing in the input is executed or fetched (basicbar#20). */

function parseBody(html: string): HTMLElement {
  return new DOMParser().parseFromString(html, "text/html").body;
}

/** The visible text of an HTML fragment, whitespace-trimmed. */
export function stripHtml(html: string): string {
  if (!html) return "";
  return parseBody(html).textContent?.trim() ?? "";
}

/** True when a stored rich-text value carries no content: no visible text and
 * no image. An editor that was opened and closed again leaves `<p></p>`
 * behind — that is empty; an image-only caption is not. */
export function isEmptyHtml(html: string | null | undefined): boolean {
  if (!html) return true;
  const body = parseBody(html);
  if (body.textContent?.trim()) return false;
  return !body.querySelector("img");
}
