/// <reference types="vitest/config" />
import { fileURLToPath } from "node:url";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Vite + React configuration (Doc 05, Doc 08 §16 — static, hash-versioned build).
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // ESM-safe absolute path to src/ (no __dirname; works under "type": "module").
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    // Proxy API + probes to the backend during local development so the SPA
    // uses same-origin relative URLs (Doc 04 §2).
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/health": { target: "http://localhost:8000", changeOrigin: true },
      "/ready": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    // "hidden" emits the .map files but omits the `//# sourceMappingURL=` comment that points
    // browsers at them. A plain `true` publishes the entire application source to anyone who
    // opens devtools on production; dropping maps entirely makes a production stack trace
    // unreadable. This keeps the artefact for symbolication (extract it from the image or upload
    // it to an error tracker) while the SPA's nginx config returns 404 for any *.map request.
    sourcemap: "hidden",
    rollupOptions: {
      output: {
        /**
         * Split only the framework libraries that every route already pulls in.
         *
         * These change on a dependency bump, not on a release, so giving them their own
         * content-hashed chunks means a normal deploy invalidates the app chunk and leaves the
         * framework cached in the browser.
         *
         * Deliberately **not** a catch-all `node_modules → vendor` rule: recharts (~400 kB) is
         * reached only through the lazily-loaded analytics route, and a catch-all would hoist it
         * into a chunk that every user downloads on first paint. Returning `undefined` leaves
         * Rollup's own splitting in place, which is what keeps that route lazy.
         */
        manualChunks(id: string) {
          if (!id.includes("node_modules")) return undefined;
          if (/node_modules\/(react|react-dom|react-router|react-router-dom|scheduler)\//.test(id)) {
            return "vendor-react";
          }
          if (id.includes("node_modules/@tanstack/")) return "vendor-query";
          return undefined;
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
    // A browser resolves the client's same-origin relative URLs against the document; Node's
    // `Request` (used by openapi-fetch under test) requires an absolute URL, so tests get an
    // explicit origin. Production still defaults to same-origin.
    env: { VITE_API_BASE_URL: "http://localhost" },
  },
});
