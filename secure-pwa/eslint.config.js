import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist", "dev-dist", "coverage", "node_modules"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2022,
      globals: { ...globals.browser, ...globals.serviceworker },
    },
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // Pages load data with `useEffect(() => void load(), [load])`; state is set after an await,
      // which this React Compiler rule cannot distinguish from a synchronous setState.
      "react-hooks/set-state-in-effect": "off",
      // Security: no string-to-code, no raw HTML injection.
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      "no-restricted-properties": [
        "error",
        { object: "localStorage", message: "Never store auth state in localStorage." },
        {
          object: "sessionStorage",
          property: "setItem",
          message: "Never store auth state in sessionStorage.",
        },
      ],
      "no-restricted-syntax": [
        "error",
        {
          selector: "JSXAttribute[name.name='dangerouslySetInnerHTML']",
          message: "Raw HTML injection is not allowed.",
        },
      ],
    },
  },
);
