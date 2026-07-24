import { defineConfig } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL;
if (!baseURL) throw new Error("E2E_BASE_URL is required");

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  outputDir: "/artifacts/playwright-results",
  reporter: [
    ["line"],
    ["junit", { outputFile: "/artifacts/playwright-junit.xml" }],
  ],
  use: {
    baseURL,
    browserName: "chromium",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
});
