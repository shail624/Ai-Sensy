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
    sourcemap: true,
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: true,
  },
});
