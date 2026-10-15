/// <reference types="vitest/config" />
// QMS OS admin web UI (docs/adr/0007-admin-web-frontend.md). Served by the API on the same origin (R-66): the build
// goes to dist/, which qms_os/main.py serves; in development the dev server proxies /api to the local API so the
// browser still sees one origin. No environment value reaches the bundle (R-70): no prefix exposes variables.
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  envPrefix: "QMS_UI_NEVER_EXPOSED_",
  build: { outDir: "dist", sourcemap: false, emptyOutDir: true },
  server: {
    host: "127.0.0.1",
    proxy: { "/api": { target: "http://127.0.0.1:8000", changeOrigin: false } },
  },
  test: { environment: "jsdom", include: ["src/**/*.test.tsx", "src/**/*.test.ts"] },
});
