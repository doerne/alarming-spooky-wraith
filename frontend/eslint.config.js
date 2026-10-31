import js from "@eslint/js";
import boundaries from "eslint-plugin-boundaries";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import globals from "globals";
import tseslint from "typescript-eslint";
import requireTestid from "./eslint-rules/require-testid.js";

export default tseslint.config(
  { ignores: ["dist", "coverage", "node_modules"] },

  // ---------------------------------------------------------- Basis + Clean Code
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    languageOptions: { ecmaVersion: 2023, globals: globals.browser },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      boundaries,
      local: { rules: { "require-testid": requireTestid } },
    },
    settings: {
      "import/resolver": { typescript: { project: "./tsconfig.app.json" } },
      "boundaries/include": ["src/**/*"],
      "boundaries/elements": [
        { type: "app", pattern: "src/app" },
        { type: "feature", pattern: "src/features/*", capture: ["feature"] },
        { type: "shared", pattern: "src/shared" },
      ],
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],

      // IDs für Tests und Automatisierung
      "local/require-testid": "error",

      // Clean Architecture: app → features → shared, Features untereinander isoliert
      "boundaries/element-types": [
        "error",
        {
          default: "disallow",
          message: "${file.type} darf ${dependency.type} nicht importieren (Clean Architecture)",
          rules: [
            { from: "app", allow: ["app", "feature", "shared"] },
            { from: "feature", allow: ["shared", ["feature", { feature: "${from.feature}" }]] },
            { from: "shared", allow: ["shared"] },
          ],
        },
      ],

      // Clean Code
      complexity: ["error", 8],
      "max-depth": ["error", 3],
      "max-params": ["error", 4],
      "max-lines-per-function": ["warn", { max: 60, skipBlankLines: true, skipComments: true }],
      "max-lines": ["warn", { max: 250, skipBlankLines: true, skipComments: true }],
      "no-nested-ternary": "error",
      eqeqeq: ["error", "always"],
    },
  },

  // shadcn-Primitives: generierter Code, reicht Props per Spread durch
  // Stilregeln aus, da die Primitives nicht von Hand geändert, sondern eingewickelt werden
  {
    files: ["src/shared/ui/**"],
    rules: {
      "local/require-testid": "off",
      "react-refresh/only-export-components": "off",
      "max-lines-per-function": "off",
      "max-lines": "off",
      complexity: "off",
      "max-depth": "off",
      "max-params": "off",
      "no-nested-ternary": "off",
      eqeqeq: "off",
    },
  },

  { files: ["**/*.test.{ts,tsx}"], rules: { "max-lines-per-function": "off" } },

  {
    files: ["eslint-rules/**/*.js", "*.config.{js,ts}"],
    languageOptions: { globals: globals.node },
  },
);
