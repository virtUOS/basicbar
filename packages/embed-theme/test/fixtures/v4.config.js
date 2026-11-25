// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 Universität Osnabrück (virtUOS)

import { themeColorsV4, themeBorderRadius, themeFontFamily } from "../../tailwind.js";

export default {
  theme: {
    extend: {
      colors: { theme: themeColorsV4 },
      borderRadius: themeBorderRadius,
      fontFamily: themeFontFamily,
    },
  },
};
