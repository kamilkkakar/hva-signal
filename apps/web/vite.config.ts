import path from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const root = path.dirname(fileURLToPath(import.meta.url));
const apiUpstream =
  process.env.API_UPSTREAM ??
  process.env.API_BASE_URL ??
  "http://127.0.0.1:8000";
const apiProxy = {
  "/api": apiUpstream,
  "/health": apiUpstream,
  "/ready": apiUpstream,
};

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(root, "src"),
    },
  },
  build: {
    // Keep MapLibre off the first HTML. A named maplibre manualChunk is
    // modulepreload'd and its CSS is linked in index.html (~800 kB).
    modulePreload: {
      resolveDependencies(_filename, deps) {
        return deps.filter(
          (dep) => !dep.includes("maplibre") && !dep.includes("MapStage"),
        );
      },
    },
  },
  server: {
    port: 5173,
    proxy: apiProxy,
  },
  preview: {
    port: 4173,
    proxy: apiProxy,
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
