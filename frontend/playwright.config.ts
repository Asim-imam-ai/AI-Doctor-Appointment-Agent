import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  use: {
    baseURL: "http://127.0.0.1:4173",
    ...devices["Desktop Chrome"],
    channel: "chrome",
  },
  webServer: {
    command: "npm.cmd run dev -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173",
    reuseExistingServer: !process.env.CI,
    env: {
      VITE_SUPABASE_URL: "https://e2e.supabase.co",
      VITE_SUPABASE_PUBLISHABLE_KEY: "browser-test-key",
    },
  },
});
