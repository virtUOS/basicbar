// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** Separate entry (`@basicbar/ui/rich-text-editor`) so the TipTap/ProseMirror
 * dependency only lands in bundles that actually render the editor — the main
 * entry stays free of it. `RichText` (the renderer) has no such dependency
 * and lives in the main entry. */
export { RICH_TEXT_TOOLS, RichTextEditor } from "./RichTextEditor";
export type { InsertedImage, RichTextEditorProps, RichTextTool } from "./RichTextEditor";
