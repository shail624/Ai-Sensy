import { defineConfig } from "@playwright/test";

const baseURL = process.env.E2E_BASE_URL;
if (!baseURL) throw new Error("E2E_BASE_URL is required");

// Artifacts land in the release image's mount by default; a workstation or agent run that has no
// /artifacts points E2E_ARTIFACTS_DIR somewhere writable instead. The container gate keeps the
// path it has always written to.
const artifacts = process.env.E2E_ARTIFACTS_DIR ?? "/artifacts";
// Playwright normally uses the browser it downloaded for its own version. Where one is already
// provisioned — a prepared image, an agent sandbox — E2E_CHROMIUM_PATH points at it rather than
// forcing a second download of the same browser.
const executablePath = process.env.E2E_CHROMIUM_PATH;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 300_000,
  expect: { timeout: 15_000 },
  outputDir: `${artifacts}/playwright-results`,
  reporter: [
    ["line"],
    ["junit", { outputFile: `${artifacts}/playwright-junit.xml` }],
  ],
  use: {
    baseURL,
    browserName: "chromium",
    headless: true,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    ...(executablePath ? { launchOptions: { executablePath } } : {}),
  },
});
