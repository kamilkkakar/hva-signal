import { existsSync } from "node:fs";
import { defineConfig, devices } from "@playwright/test";

/**
 * Local e2e must start its own API + preview. Foreign listeners on
 * :8000 / :4173 are common in this workspace and must not be reused.
 * CI still starts :8000 / :4173 itself and leaves webServer undefined.
 */
const isolated = !process.env.CI;
const apiPort = process.env.PLAYWRIGHT_API_PORT ?? (isolated ? "18003" : "8000");
const webPort = process.env.PLAYWRIGHT_WEB_PORT ?? (isolated ? "14173" : "4173");
const apiBase = isolated
  ? `http://127.0.0.1:${apiPort}`
  : (process.env.API_BASE_URL ?? `http://127.0.0.1:${apiPort}`);
const webBase = isolated
  ? `http://127.0.0.1:${webPort}`
  : (process.env.WEB_BASE_URL ?? `http://127.0.0.1:${webPort}`);

if (isolated) {
  process.env.API_BASE_URL = apiBase;
  process.env.WEB_BASE_URL = webBase;
}

function apiUvicornCommand(): string {
  const args = `-m uvicorn app.main:app --host 127.0.0.1 --port ${apiPort}`;
  if (existsSync("./apps/api/.venv/Scripts/python.exe")) {
    return `.venv\\Scripts\\python.exe ${args}`;
  }
  if (existsSync("./apps/api/.venv/bin/python")) {
    return `.venv/bin/python ${args}`;
  }
  return `python ${args}`;
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
          reuseExistingServer: false,
          timeout: 120_000,
          env: {
            DATA_MODE: "replay",
            CACHE_DIR: ".cache/empty-replay-q3",
          },
        },
        {
          command: `npm run preview -- --host 127.0.0.1 --port ${webPort} --strictPort`,
          cwd: "./apps/web",
          url: webBase,
          reuseExistingServer: false,
          timeout: 120_000,
          env: {
            API_BASE_URL: apiBase,
            API_UPSTREAM: apiBase,
          },
        },
      ],
});
