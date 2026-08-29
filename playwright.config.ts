import { existsSync } from "node:fs";
import { defineConfig, devices } from "@playwright/test";

const webBase = process.env.WEB_BASE_URL ?? "http://127.0.0.1:4173";
const apiBase = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";

function apiUvicornCommand(): string {
  if (existsSync("./apps/api/.venv/Scripts/python.exe")) {
    return ".venv\\Scripts\\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000";
  }
  if (existsSync("./apps/api/.venv/bin/python")) {
    return ".venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000";
  }
  return "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000";
}

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["github"], ["list"]] : "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: webBase,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: process.env.CI
    ? undefined
    : [
        {
          command: apiUvicornCommand(),
          cwd: "./apps/api",
          url: `${apiBase}/health`,
          reuseExistingServer: true,
          env: { DATA_MODE: "replay", CACHE_DIR: ".cache/empty-replay" },
        },
        {
          command: "npm run preview -- --host 127.0.0.1 --port 4173",
          cwd: "./apps/web",
          url: webBase,
          reuseExistingServer: true,
        },
      ],
});
