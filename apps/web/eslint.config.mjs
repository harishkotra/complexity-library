import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";

export default defineConfig([
  ...nextVitals,
  globalIgnores([".next/**", "apps/web/.next/**", "node_modules/**", "apps/web/node_modules/**"]),
  {
    rules: {
      // Client-side tool surfaces intentionally use native anchors for simple hard navigations.
      "@next/next/no-html-link-for-pages": "off",
      // Data-loading and playback effects intentionally synchronize local UI state.
      "react-hooks/set-state-in-effect": "off",
    },
  },
]);
