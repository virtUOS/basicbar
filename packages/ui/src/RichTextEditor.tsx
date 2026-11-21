// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

/** The shared WYSIWYG editor for formatted long-form fields across the -bar
 * tools: bold, italic, lists, link, headings (H2/H3), and — when the host
 * app wires up `onUploadImage` — images. Stores HTML; the backend sanitizes
 * to exactly this subset (e.g. `basicbar_integrations.html_sanitize.clean_html`)
 * — anything else is stripped. Short fields (titles, options) stay plain and
 * should not use this. Moved from AbstimmBAR (#49) so all -bar tools share
 * one implementation. */
// Bold ships inside @tiptap/starter-kit (same pinned version); we import it
// directly (a listed dependency, pinned to the same version) only to
// override its parse rules.
import Bold from "@tiptap/extension-bold";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import { NodeSelection, type Transaction } from "@tiptap/pm/state";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import {
  Bold as BoldIcon,
  Captions,
  Heading2,
  Heading3,
  ImagePlus,
  Italic as ItalicIcon,
  Link as LinkIcon,
  List,
  ListOrdered,
  X,
} from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { usePromptDialog } from "./PromptDialog";

/** Bold that only recognises explicit <strong>/<b> tags. TipTap's default
 * also parses any `font-weight: 500–900` as bold — so text typed after a
 * DOM reparse or pasted from Word/PDF turned bold on its own. We bold only
 * via the toolbar (which emits <strong>, the one tag the backend keeps). */
const PlainBold = Bold.extend({
  parseHTML() {
    return [{ tag: "strong" }, { tag: "b" }];
  },
});

/** Image with a transient, never-rendered `uploadToken` attribute: a freshly
 * uploaded image is inserted right away (alt="") carrying a token unique to
 * that upload, so its alt text can be set on exactly that node once the
 * description dialog resolves — even if other uploads landed in the
 * meantime. The token never reaches the HTML (`rendered: false`, not
 * parsed), and is cleared once the dialog is done. */
const UploadImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      uploadToken: { default: null, rendered: false, parseHTML: () => null, keepOnSplit: false },
    };
  },
});

/** What `onImageInserted` receives: the image's `src`, its current `alt`
 * ("" right after an upload), whether it was just uploaded ("insert", with
 * the uploaded `file`) or the "Image description" button was used ("edit"). */
export interface InsertedImage {
  src: string;
  alt: string;
  mode: "insert" | "edit";
  file?: File;
}

/** Follows a document position through later transactions (other uploads,
 * typing, an outside value sync). `deleted` turns true once the content
 * right after the position (e.g. the image node starting there) is gone. */
function trackPosition(editor: Editor, pos: number) {
  const tracked = {
    pos,
    deleted: false,
    stop: () => editor.off("transaction", onTransaction),
  };
  function onTransaction({ transaction }: { transaction: Transaction }) {
    const mapped = transaction.mapping.mapResult(tracked.pos, 1);
    tracked.pos = mapped.pos;
    if (mapped.deletedAfter) tracked.deleted = true;
  }
  editor.on("transaction", onTransaction);
  return tracked;
}

export interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  /** Upload an image and resolve to its relative URL (e.g. "/media/rich/x.png").
   *  Omit to disable images (no button; dropped/pasted image files ignored).
   *  Pasting rich HTML (e.g. copied from a web page) is gated too: any
   *  `<img>` whose `src` does not start with "/media/" is stripped from the
   *  pasted content — so an external image can never sneak in through paste,
   *  bypassing the upload flow and the "/media/…"-only contract the backend
   *  enforces. With this prop omitted, every pasted `<img>` is stripped.
   *  Existing images already in `value` are unaffected — this only filters
   *  newly pasted HTML, not the initial/external content load. */
  onUploadImage?: (file: File) => Promise<string>;
  /** Asks for an image's description (alt text) with the host app's own
   *  dialog, e.g. one that also offers an AI suggestion or credit fields.
   *  "insert": called once `onUploadImage` resolved — the image is already
   *  in the document with `alt=""`; resolve `{ alt }` to set it, `null` to
   *  keep it empty (decorative). "edit": called by the "Image description"
   *  button with the selected image's src/alt; `null` = no change. A
   *  rejected promise counts as `null`. Calls never overlap: a second
   *  upload's call waits until the first one resolved. Omitted: the editor
   *  asks with its own built-in dialog (one text field). */
  onImageInserted?: (image: InsertedImage) => Promise<{ alt: string } | null>;
  ariaLabel?: string;
  /** Id of an external `<label>` naming this editor (sets `aria-labelledby`
   *  on the editable element); an alternative to `ariaLabel` when a visible
   *  label already exists (e.g. `TranslatableField`'s `labelId`). */
  labelledBy?: string;
  /** Ids of helper texts describing this editor (sets `aria-describedby`),
   *  e.g. `TranslatableField`'s `describedBy`. */
  describedBy?: string;
  id?: string;
  /** `false` renders the content read-only in the editor's own frame — no
   *  toolbar, no caret, pasted/dropped files ignored — e.g. while a form is
   *  saving or for a viewer without edit rights. Default `true`. (Pure
   *  display of stored HTML is `RichText`, which costs no TipTap.) */
  editable?: boolean;
}

function ToolbarButton({
  active,
  disabled,
  label,
  onClick,
  children,
}: {
  active?: boolean;
  disabled?: boolean;
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      // aria-disabled (not native disabled) keeps the button in the tab order,
      // so keyboard users can discover it before selecting an image.
      aria-disabled={disabled || undefined}
      onMouseDown={(event) => event.preventDefault()}
      onClick={disabled ? undefined : onClick}
      className={`rounded px-2 py-1 text-sm ${
        disabled
          ? "cursor-not-allowed text-slate-400 opacity-50 dark:text-slate-600"
          : active
            ? "bg-brand-100 dark:bg-brand-900 text-brand-800 dark:text-brand-200"
            : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
      }`}
    >
      {children}
    </button>
  );
}

export function RichTextEditor({
  value,
  onChange,
  onUploadImage,
  onImageInserted,
  ariaLabel,
  labelledBy,
  describedBy,
  id,
  editable = true,
}: RichTextEditorProps) {
  const { t } = useTranslation();
  const { dialog: promptDialog, prompt } = usePromptDialog();
  // Detail of the last failed upload ("" = no message), shown under the
  // toolbar until dismissed or the next upload succeeds; null = none.
  const [uploadError, setUploadError] = useState<string | null>(null);
  const tokenPrefix = useId();
  // Dialogs (alt text, link URL — built-in or the host's) run strictly one
  // after another, in request order: two uploads finishing back to back must
  // not open two dialogs at once or answer each other's question.
  const dialogs = useRef({ chain: Promise.resolve(), pending: 0, nextToken: 1 }).current;
  // The editor's paste/drop handlers are created once (first render); they
  // reach the current host callbacks (often fresh closures per render, e.g.
  // over the active language) through this ref.
  const callbacks = useRef({ onUploadImage, onImageInserted });
  callbacks.current = { onUploadImage, onImageInserted };

  // Echo bookkeeping for the outside-value sync below. Our own edits come
  // back as `value` one render later — and under load the user may type
  // again before the sync effect runs, so that echo is already stale. We
  // remember what we emitted to tell such echoes apart from genuine outside
  // changes.
  const sync = useRef({
    // The `value` prop the sync effect saw last.
    prop: value,
    // Newest HTML emitted via onChange (null: none since the last outside
    // change), and every emission the parent hasn't caught up with yet (any
    // of them may still come back as `value`).
    latest: null as string | null,
    pending: new Set<string>(),
  }).current;

  function serialized<T>(editor: Editor, ask: () => Promise<T>): Promise<T> {
    dialogs.pending += 1;
    const run = dialogs.chain.then(ask);
    dialogs.chain = run.then(
      () => undefined,
      () => undefined,
    );
    return run.finally(() => {
      dialogs.pending -= 1;
      // Back to the editor once the last queued dialog is done (the native
      // <dialog> restores focus too, but a host dialog may not).
      if (dialogs.pending === 0 && !editor.isDestroyed) editor.commands.focus();
    });
  }

  /** The new alt text (trimmed), or null for "no change"/cancelled. */
  function askAlt(editor: Editor, image: InsertedImage): Promise<string | null> {
    return serialized(editor, async () => {
      if (editor.isDestroyed) return null; // queued, but the editor is gone
      const { onImageInserted } = callbacks.current;
      if (onImageInserted) {
        try {
          const answer = await onImageInserted(image);
          return answer ? answer.alt.trim() : null;
        } catch {
          return null;
        }
      }
      const answer = await prompt({
        label: t("Image description (alt text)"),
        defaultValue: image.alt,
      });
      return answer === null ? null : answer.trim();
    });
  }

  async function insertImageFile(editor: Editor, file: File, dropPos?: number) {
    const { onUploadImage } = callbacks.current;
    if (!onUploadImage || !editor.isEditable) return;
    // A drop position must survive edits made while the upload runs.
    const drop = dropPos === undefined ? null : trackPosition(editor, dropPos);
    // Only a new attempt clears an old failure notice — a parallel upload's
    // success must not hide another one's failure.
    setUploadError(null);
    let url: string;
    try {
      url = await onUploadImage(file);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "");
      return;
    } finally {
      drop?.stop();
    }
    if (editor.isDestroyed) return;
    // Insert first (alt=""), ask afterwards (WCAG 1.1.1): skipping the
    // dialog leaves a decorative image, never a lost upload.
    const token = `${tokenPrefix}-${dialogs.nextToken++}`;
    const image = { type: "image", attrs: { src: url, alt: "", uploadToken: token } };
    const { selection } = editor.state;
    if (drop) editor.chain().insertContentAt(drop.pos, image).run();
    // A still-selected image (e.g. the previous upload) must not be replaced.
    else if (selection instanceof NodeSelection) editor.chain().insertContentAt(selection.to, image).run();
    else editor.chain().insertContent(image).run();

    const alt = await askAlt(editor, { src: url, alt: "", mode: "insert", file });
    if (editor.isDestroyed) return;
    let at: number | null = null;
    // Fallback: an outside setContent (re-parsed HTML) drops the token; then
    // the one image with this src and no alt yet is ours — if unambiguous.
    const bySrc: number[] = [];
    editor.state.doc.descendants((node, pos) => {
      if (node.type.name !== "image") return true;
      if (node.attrs.uploadToken === token) at = pos;
      else if (node.attrs.src === url && !node.attrs.alt) bySrc.push(pos);
      return true;
    });
    if (at === null && bySrc.length === 1) at = bySrc[0];
    if (at === null) return; // removed meanwhile (deleted, undone, replaced)
    const tr = editor.state.tr.setNodeAttribute(at, "uploadToken", null);
    if (alt) tr.setNodeAttribute(at, "alt", alt);
    // Clearing the token alone is bookkeeping, not an undoable edit.
    else tr.setMeta("addToHistory", false);
    editor.view.dispatch(tr);
  }

  const editor = useEditor({
    // @tiptap/react v3 no longer re-renders on every transaction by default
    // (perf choice — see `useEditorState`); we do want that, though: the
    // toolbar reads `editor.isActive(...)` directly in the render body for
    // every button (Bold/Italic/headings/link and now "Image description"),
    // so a selection-only change (e.g. clicking into/out of an image, no
    // document change) must still re-render this component or those buttons
    // go stale until the next actual edit.
    shouldRerenderOnTransaction: true,
    // TipTap would otherwise append a <style data-tiptap-style> to <head> at
    // runtime, which a CSP with `style-src 'self'` (no 'unsafe-inline')
    // blocks (ausleihbar#44/#45, basicbar#9). The same ProseMirror base rules
    // ship in base.css instead.
    injectCSS: false,
    editable,
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3] },
        blockquote: false,
        codeBlock: false,
        code: false,
        horizontalRule: false,
        link: false,
        bold: false,
        // The toolbar never offers underline/strikethrough, and the backend
        // sanitizer strips both — registering them would let a user format
        // text (e.g. via a keyboard shortcut) that silently vanishes on save.
        underline: false,
        strike: false,
      }),
      PlainBold,
      // Links may point anywhere; the backend forces rel="noopener" itself,
      // so we don't render one here (any value we chose would just be
      // overwritten). We do not open a new tab (target), and we do not
      // auto-link typed URLs (toolbar only).
      Link.configure({
        openOnClick: false,
        autolink: false,
        HTMLAttributes: { target: null, rel: null },
      }),
      // Kept unconditionally so existing <img> content survives even when
      // this instance has no onUploadImage (view-only fields, other tools'
      // legacy content, …) — only insertion is gated on onUploadImage.
      UploadImage,
    ],
    content: value,
    onUpdate: ({ editor }) => {
      const html = editor.getHTML();
      sync.latest = html;
      sync.pending.add(html);
      onChange(html);
    },
    editorProps: {
      attributes: {
        ...(id ? { id } : {}),
        ...(ariaLabel ? { "aria-label": ariaLabel } : {}),
        ...(labelledBy ? { "aria-labelledby": labelledBy } : {}),
        role: "textbox",
        "aria-multiline": "true",
        class:
          // Match the single-line inputs' ink so typed text is crisp in both
          // themes (the editor otherwise inherits a dim slate-400/500).
          "text-slate-900 dark:text-slate-100 " +
          // The editable fills the frame edge-to-edge, so the global
          // :focus-visible ring (base.css) would bulge out past the border and
          // look wider than the toolbar. Suppress the ring — the container's
          // focus-within:border-brand-600 already signals focus. A transparent
          // outline is kept on purpose so forced-colors mode (Windows contrast
          // themes) still shows a focus indicator.
          "min-h-28 max-h-[420px] overflow-y-auto rounded-lg px-3 py-2 " +
          "focus:[outline:2px_solid_transparent] focus:[outline-offset:2px] focus-visible:[outline:2px_solid_transparent] focus-visible:[outline-offset:2px] focus-visible:ring-0 focus-visible:ring-offset-0 " +
          "[&_img]:max-w-full [&_img]:h-auto [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 " +
          "[&_p]:my-1 [&_li]:my-0.5 [&_h2]:mt-2 [&_h2]:mb-1 [&_h2]:text-xl [&_h2]:font-bold " +
          "[&_h3]:mt-2 [&_h3]:mb-1 [&_h3]:text-base [&_h3]:font-semibold " +
          "[&_a]:text-brand-700 [&_a]:underline dark:[&_a]:text-brand-300",
      },
      handleDrop: (view, event) => {
        if (!onUploadImage) return false;
        const file = event.dataTransfer?.files?.[0];
        if (file && file.type.startsWith("image/") && editor) {
          event.preventDefault();
          const at = view.posAtCoords({ left: event.clientX, top: event.clientY });
          void insertImageFile(editor, file, at?.pos);
          return true;
        }
        return false;
      },
      handlePaste: (_view, event) => {
        if (!onUploadImage) return false;
        const file = Array.from(event.clipboardData?.files ?? []).find((f) =>
          f.type.startsWith("image/"),
        );
        if (file && editor) {
          event.preventDefault();
          void insertImageFile(editor, file);
          return true;
        }
        return false;
      },
      // Rich HTML paste (e.g. copied from a web page) goes through ProseMirror's
      // HTML parser, not handlePaste above — so an <img src="https://…"> would
      // otherwise slip straight into the document without ever calling
      // onUploadImage, and without the backend's "/media/…"-only contract
      // catching it until save (leaving a broken bare <img> behind). Strip
      // every pasted <img> that isn't already a "/media/…" reference; strip
      // all of them when onUploadImage is omitted (images disabled entirely).
      // Only pasted HTML passes through here — the initial `content: value`
      // load below never calls this, so existing images are unaffected.
      transformPastedHTML: (html) => {
        const doc = new DOMParser().parseFromString(html, "text/html");
        doc.body.querySelectorAll("img").forEach((img) => {
          const src = img.getAttribute("src") ?? "";
          if (!onUploadImage || !src.startsWith("/media/")) img.remove();
        });
        return doc.body.innerHTML;
      },
    },
  });

  // Sync when the value changes from OUTSIDE (e.g. applying an AI rephrasing,
  // switching the active language tab, a form reset). Echoes of our own edits
  // are ignored — the current one and stale ones alike: under load a
  // keystroke can land between the render carrying an echo and this effect,
  // and resetting to that older text would drop the newest keystroke (and
  // for good a trailing space, which ProseMirror strips on parse). A change
  // of the prop that is not a pending own emission is external and applied,
  // even when it equals an earlier text (e.g. resetting a field to "").
  // emitUpdate:false so this settles without a second round that would reset
  // the caret to the top while the user is typing (#50). addToHistory:false
  // keeps this out of the undo stack — otherwise a single Ctrl+Z right after
  // an external sync (e.g. switching language tabs) would undo INTO the
  // previous tab's content instead of the user's own last edit.
  useEffect(() => {
    if (!editor) return;
    if (value === sync.prop) {
      // Prop unchanged (e.g. the editor instance just became available):
      // align only if the user hasn't edited yet.
      if (sync.latest !== null) return;
    } else {
      sync.prop = value;
      if (value === sync.latest) {
        // Caught up with the newest emission: older ones can't come back.
        sync.pending.clear();
        return;
      }
      if (sync.pending.has(value)) return; // stale own echo
      // Outside change: forget our emissions.
      sync.latest = null;
      sync.pending.clear();
    }
    if (value !== editor.getHTML()) {
      editor.chain().setMeta("addToHistory", false).setContent(value, { emitUpdate: false }).run();
    }
  }, [editor, value, sync]);

  // `editable` in useEditor only seeds the initial state; flips afterwards
  // (e.g. a form toggling into "saving") go through setEditable.
  useEffect(() => {
    if (editor && editor.isEditable !== editable) editor.setEditable(editable);
  }, [editor, editable]);

  // Not in `editorProps.attributes`: those are read once and re-applied by
  // ProseMirror on every update, but the described-by set changes at runtime
  // (e.g. a required-field error appearing), so it is synced directly.
  useEffect(() => {
    if (!editor) return;
    const apply = () => {
      // Before mount `editor.view` is a stub that throws on `dom`.
      if (!editor.isInitialized || editor.isDestroyed) return;
      const dom = editor.view.dom;
      if (describedBy) dom.setAttribute("aria-describedby", describedBy);
      else dom.removeAttribute("aria-describedby");
    };
    apply();
    editor.on("create", apply);
    return () => {
      editor.off("create", apply);
    };
  }, [editor, describedBy]);

  if (!editor) return null;

  async function setLink() {
    if (!editor) return;
    const previous = (editor.getAttributes("link").href as string) || "";
    // The selection does not survive the modal dialog (Firefox, and Chromium
    // after a double-click selection, collapse it to the start once the
    // dialog closes and focus returns), so remember the range — following it
    // through edits made meanwhile, e.g. an upload finishing — and restore it.
    const from = trackPosition(editor, editor.state.selection.from);
    const to = trackPosition(editor, editor.state.selection.to);
    try {
      const answer = await serialized(editor, async () =>
        editor.isDestroyed ? null : prompt({ label: t("Enter URL"), defaultValue: previous }),
      );
      if (answer === null || editor.isDestroyed) return; // cancelled
      const url = answer.trim();
      const range = { from: Math.min(from.pos, to.pos), to: Math.max(from.pos, to.pos) };
      const chain = editor.chain().focus().setTextSelection(range).extendMarkRange("link");
      if (url === "") chain.unsetLink().run();
      else chain.setLink({ href: url }).run();
    } finally {
      from.stop();
      to.stop();
    }
  }

  async function setImageAlt() {
    if (!editor) return;
    const { selection } = editor.state;
    if (!(selection instanceof NodeSelection) || selection.node.type.name !== "image") return;
    const src = selection.node.attrs.src as string;
    // Follow the node: an upload finishing while the dialog is open shifts it.
    const image = trackPosition(editor, selection.from);
    try {
      const alt = await askAlt(editor, {
        src,
        alt: (selection.node.attrs.alt as string | null) ?? "",
        mode: "edit",
      });
      if (alt === null || image.deleted || editor.isDestroyed) return; // cancelled / gone
      const node = editor.state.doc.nodeAt(image.pos);
      if (node?.type.name !== "image" || node.attrs.src !== src) return;
      editor.view.dispatch(editor.state.tr.setNodeAttribute(image.pos, "alt", alt));
    } finally {
      image.stop();
    }
  }

  return (
    // The frame stays the single root element for the host (`space-y-*`,
    // :last-child). The prompt <dialog> lives inside it: closed it is
    // display:none, open it sits in the top layer — no layout impact.
    <div
      className={`rounded-lg border border-field focus-within:ring-2 focus-within:ring-brand-600 focus-within:ring-offset-2 focus-within:ring-offset-white dark:focus-within:ring-offset-slate-950 ${
        editable ? "" : "bg-slate-50 dark:bg-slate-900"
      }`}
    >
      {editable && (
        // Wraps onto further rows on narrow screens instead of a horizontal
        // scroller whose hidden buttons had no affordance.
        <div className="flex flex-wrap gap-1 border-b border-slate-200 dark:border-slate-800 px-2 py-1">
          <ToolbarButton
            label={t("Bold")}
            active={editor.isActive("bold")}
            onClick={() => editor.chain().focus().toggleBold().run()}
          >
            <BoldIcon aria-hidden className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            label={t("Italic")}
            active={editor.isActive("italic")}
            onClick={() => editor.chain().focus().toggleItalic().run()}
          >
            <ItalicIcon aria-hidden className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            label={t("Heading (large)")}
            active={editor.isActive("heading", { level: 2 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          >
            <Heading2 aria-hidden className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            label={t("Heading (small)")}
            active={editor.isActive("heading", { level: 3 })}
            onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          >
            <Heading3 aria-hidden className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            label={t("Bulleted list")}
            active={editor.isActive("bulletList")}
            onClick={() => editor.chain().focus().toggleBulletList().run()}
          >
            <List aria-hidden className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            label={t("Numbered list")}
            active={editor.isActive("orderedList")}
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
          >
            <ListOrdered aria-hidden className="h-4 w-4" />
          </ToolbarButton>
          <ToolbarButton
            label={t("Link")}
            active={editor.isActive("link")}
            onClick={() => void setLink()}
          >
            <LinkIcon aria-hidden className="h-4 w-4" />
          </ToolbarButton>
          {onUploadImage && (
            <label
              className="flex cursor-pointer items-center rounded px-2 py-1 text-sm text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 focus-within:ring-2 focus-within:ring-brand-600 focus-within:ring-offset-1"
              title={t("Insert image (or drag and drop)")}
            >
              <ImagePlus aria-hidden className="h-4 w-4" />
              <input
                type="file"
                accept="image/*"
                aria-label={t("Insert image (or drag and drop)")}
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void insertImageFile(editor, file);
                  event.target.value = "";
                }}
              />
            </label>
          )}
          {onUploadImage && (
            <ToolbarButton
              label={t("Image description")}
              disabled={!editor.isActive("image")}
              onClick={() => void setImageAlt()}
            >
              <Captions aria-hidden className="h-4 w-4" />
            </ToolbarButton>
          )}
        </div>
      )}
      {uploadError !== null && (
        <div
          role="alert"
          className="flex items-start justify-between gap-2 border-b border-slate-200 px-3 py-2 text-sm text-danger dark:border-slate-800"
        >
          <span>
            {t("Image upload failed")}
            {uploadError ? `: ${uploadError}` : ""}
          </span>
          <button
            type="button"
            title={t("Dismiss")}
            aria-label={t("Dismiss")}
            onClick={() => setUploadError(null)}
            className="rounded p-0.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            <X aria-hidden className="h-4 w-4" />
          </button>
        </div>
      )}
      <EditorContent editor={editor} />
      {promptDialog}
    </div>
  );
}
