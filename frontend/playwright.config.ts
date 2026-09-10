import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  use: {
    ...devices["Desktop Chrome"],
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "fixture",
      testMatch: "workbench.spec.ts",
      use: { baseURL: "http://127.0.0.1:5174" },
    },
    {
      name: "api",
      testMatch: "api.spec.ts",
      use: { baseURL: "http://127.0.0.1:5175" },
    },
  ],
  webServer: [
    {
      command:
        "VITE_DATA_SOURCE=fixture VITE_STRATEGY_ID=demo-project-planning npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: !process.env.CI,
    },
    {
      command:
        "VITE_DATA_SOURCE=api VITE_STRATEGY_ID=demo-project-planning EVOTEAM_PROXY_TARGET=http://127.0.0.1:8765 npm run dev -- --port 5175 --strictPort",
      url: "http://127.0.0.1:5175",
      reuseExistingServer: !process.env.CI,
    },
    {
      command: "uv run python -m frontend.e2e.serve_api",
      cwd: "..",
      url: "http://127.0.0.1:8765/health",
      reuseExistingServer: false,
    },
  ],
});
