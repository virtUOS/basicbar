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
} from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

/** Bold that only recognises explicit <strong>/<b> tags. TipTap's default
 * also parses any `font-weight: 500–900` as bold — so text typed after a
 * DOM reparse or pasted from Word/PDF turned bold on its own. We bold only
 * via the toolbar (which emits <strong>, the one tag the backend keeps). */
const PlainBold = Bold.extend({
  parseHTML() {
    return [{ tag: "strong" }, { tag: "b" }];
  },
});

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
  ariaLabel,
  labelledBy,
  describedBy,
  id,
  editable = true,
}: RichTextEditorProps) {
  const { t } = useTranslation();

  async function insertImageFile(editor: Editor, file: File, pos?: number) {
    if (!onUploadImage || !editor.isEditable) return;
    let url: string;
    try {
      url = await onUploadImage(file);
    } catch (err) {
      const detail = err instanceof Error && err.message ? `: ${err.message}` : "";
      window.alert(`${t("Image upload failed")}${detail}`);
      return;
    }
    // Ask for alt text once the upload has actually succeeded (WCAG 1.1.1);
    // empty input or Cancel both mean "no description" — the image is
    // inserted either way, just as a (possibly) decorative one.
    const alt = (window.prompt(t("Image description (alt text)"), "") ?? "").trim();
    const chain = editor.chain().focus();
    if (pos !== undefined) chain.insertContentAt(pos, { type: "image", attrs: { src: url, alt } });
    else chain.setImage({ src: url, alt });
    chain.run();
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
      Image,
    ],
    content: value,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
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
          // look wider than the toolbar. Suppress it — the container's
          // focus-within:border-brand-600 already signals focus.
          "min-h-28 max-h-[420px] overflow-y-auto rounded-lg px-3 py-2 " +
          "focus:outline-none focus-visible:outline-none focus-visible:ring-0 focus-visible:ring-offset-0 " +
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
  // or switching the active language tab). The guard avoids clobbering the
  // cursor during normal typing (there the stored value already equals the
  // editor's HTML). emitUpdate:false so this settles without a second round
  // that would reset the caret to the top while the user is typing (#50).
  // addToHistory:false keeps this out of the undo stack — otherwise a single
  // Ctrl+Z right after an external sync (e.g. switching language tabs) would
  // undo INTO the previous tab's content instead of the user's own last edit.
  useEffect(() => {
    if (editor && value !== editor.getHTML()) {
      editor.chain().setMeta("addToHistory", false).setContent(value, { emitUpdate: false }).run();
    }
  }, [editor, value]);

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

  function setLink() {
    if (!editor) return;
    const previous = (editor.getAttributes("link").href as string) || "";
    const url = window.prompt(t("Enter URL"), previous);
    if (url === null) return; // cancelled
    if (url === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    editor.chain().focus().extendMarkRange("link").setLink({ href: url }).run();
  }

  function setImageAlt() {
    if (!editor || !editor.isActive("image")) return;
    const previous = (editor.getAttributes("image").alt as string) ?? "";
    const alt = window.prompt(t("Image description (alt text)"), previous);
    if (alt === null) return; // cancelled: leave the current alt untouched
    editor.chain().focus().updateAttributes("image", { alt: alt.trim() }).run();
  }

  return (
    <div
      className={`rounded-lg border border-slate-300 dark:border-slate-700 focus-within:ring-2 focus-within:ring-brand-600 focus-within:ring-offset-2 focus-within:ring-offset-white dark:focus-within:ring-offset-slate-950 ${
        editable ? "" : "bg-slate-50 dark:bg-slate-900"
      }`}
    >
      {editable && (
        <div className="flex flex-nowrap gap-1 overflow-x-auto border-b border-slate-200 dark:border-slate-800 px-2 py-1">
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
            onClick={setLink}
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
              onClick={setImageAlt}
            >
              <Captions aria-hidden className="h-4 w-4" />
            </ToolbarButton>
          )}
        </div>
      )}
      <EditorContent editor={editor} />
    </div>
  );
}
