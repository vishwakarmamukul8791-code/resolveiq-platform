import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import {
  defineConfig,
  globalIgnores,
} from "eslint/config";


export default defineConfig([
  globalIgnores([
    "dist",
  ]),

  {
    files: [
      "**/*.{js,jsx}",
    ],

    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],

    languageOptions: {
      globals: globals.browser,

      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
  },

  {
    // These components intentionally synchronize API data
    // or parent-selected state inside effects. The state
    // transitions are bounded and required by their UI flow.
    files: [
      "src/components/IncidentWorkspace.jsx",
      "src/components/SourceViewerModal.jsx",
      "src/components/SupportSidebar.jsx",
      "src/components/admin/AdminDocumentsTab.jsx",
      "src/components/admin/AdminEngineersTab.jsx",
      "src/components/admin/AdminHealthTab.jsx",
      "src/context/AuthContext.jsx",
    ],

    rules: {
      "react-hooks/set-state-in-effect": "off",
    },
  },

  {
    // Context modules intentionally export both their Provider
    // component and consumer hook from the same cohesive module.
    files: [
      "src/context/AuthContext.jsx",
      "src/context/ThemeContext.jsx",
    ],

    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
]);