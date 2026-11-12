import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { loadEnv } from "vite";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    VitePWA({
      // Custom service worker: precaches the static app shell only, never API responses.
      strategies: "injectManifest",
      srcDir: "src/pwa",
      filename: "sw.ts",
      injectRegister: false, // registered from src/pwa/register.ts (no inline script, CSP-safe)
      registerType: "prompt",
      injectManifest: {
        globPatterns: ["**/*.{js,css,html,svg,png,webmanifest,woff2}"],
      },
      manifest: {
        name: "RoadSentinel",
        short_name: "RoadSentinel",
        description: "Traffic-camera alerts for police operators and patrols",
        start_url: "/",
        scope: "/",
        display: "standalone",
        background_color: "#0a0e14",
        theme_color: "#0a0e14",
        icons: [
          { src: "/icons/icon-192.png", sizes: "192x192", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png" },
          { src: "/icons/icon-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
        ],
      },
      devOptions: { enabled: false },
    }),
  ],
  build: { sourcemap: false },
  server: {
    // Dev only: proxy the API so cookies stay same-origin.
    proxy: {
      "/api": {
        target:
          loadEnv(mode, new URL(".", import.meta.url).pathname, "RS_").RS_API_ORIGIN ??
          "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: "jsdom",
    environmentOptions: { jsdom: { url: "https://localhost/" } },
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
}));
