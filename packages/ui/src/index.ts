// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

export { ThemeProvider, useTheme, prePaintScript } from "./theme";
export type { Appearance } from "./theme";

export { default as i18n, initI18n, SUPPORTED_LANGUAGES } from "./i18n";
export type { Language } from "./i18n";

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
