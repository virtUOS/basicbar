// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

export { ThemeProvider, useTheme, prePaintScript } from "./theme";
export type { Appearance } from "./theme";

export { default as i18n, initI18n, SUPPORTED_LANGUAGES } from "./i18n";
export type { Language } from "./i18n";

export {
  MAX_TRANSLATE_LENGTH,
  TRANSLATION_SLOT_MEDIA,
  TranslationControlsSlot,
  TranslationFormProvider,
  useTranslationForm,
} from "./TranslationForm";
export type {
  TranslatableEntry,
  TranslateFn,
  TranslateFormat,
} from "./TranslationForm";

export { TranslatableField } from "./TranslatableField";
export type { RenderInputArgs, TranslatableFieldProps } from "./TranslatableField";

export { AppearanceControl, LanguageOptions, PreferencesMenu } from "./Preferences";

// RichTextEditor (TipTap) deliberately lives in its own entry,
// "@basicbar/ui/rich-text-editor" — see src/rich-text-editor.ts.
export { RichText, richTextClass } from "./RichText";
export type { RichTextProps } from "./RichText";
export { isEmptyHtml, stripHtml } from "./html";

export {
  defaultContentLangLabel,
  getDefaultContentLang,
  isTranslationEnabled,
  localizedMap,
  localizedText,
  setDefaultContentLang,
  setLocalizedLang,
  setTranslationEnabled,
} from "./contentLang";
export type { LocalizedText } from "./contentLang";
