// Lint rules for the admin web UI (R-71).
import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "node_modules"] },
  {
    files: ["**/*.{ts,tsx}"],
    extends: [js.configs.recommended, ...tseslint.configs.strict],
    languageOptions: { globals: globals.browser },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "no-restricted-globals": ["error", "localStorage", "sessionStorage"],
      "no-restricted-properties": ["error",
        { object: "window", property: "localStorage", message: "R-67: no web storage" },
        { object: "window", property: "sessionStorage", message: "R-67: no web storage" },
        { object: "document", property: "cookie", message: "R-67: the session cookie is HttpOnly" }],
    },
  },
  {
    // Tests may read web storage (and, in the browser tests, document.cookie) to assert that the UI left it empty.
    files: ["src/**/*.test.{ts,tsx}", "e2e/**/*.ts"],
    rules: { "no-restricted-properties": "off", "no-restricted-globals": "off" },
  },
  { files: ["scripts/**/*.mjs"], languageOptions: { globals: globals.node } },
);
