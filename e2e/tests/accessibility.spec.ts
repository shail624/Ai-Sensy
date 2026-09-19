import { AxeBuilder } from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

/**
 * WCAG 2.1 A/AA across the authenticated application, in both themes and at phone width.
 *
 * Every module row in `MODULE_STATUS` carried "authenticated representative-data visual/WCAG
 * review" as pending, because a signed-out page proves nothing: the failures live in status chips,
 * table headers, timestamps and avatars, none of which the login screen draws. This walks the real
 * screens with a real session and asserts there is nothing left to find.
 *
 * Both themes, because the tokens differ: the first run found white-on-teal at 1.86:1 on every
 * primary button in the dark theme, which a light-only pass would never have reported.
 */

const ROUTES = [
  "/", "/contacts", "/tasks", "/downloads", "/inbox", "/chat-history",
  "/campaigns", "/broadcasts", "/templates", "/media", "/analytics",
  "/automation", "/reactivation", "/scan", "/channels", "/pipelines",
  "/segments", "/operations/overview", "/admin/users", "/admin/roles",
  "/admin/permissions", "/admin/audit", "/settings/organization", "/settings/tags",
];

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}

async function signIn(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByLabel("Email").fill(required("E2E_OWNER_EMAIL"));
  await page.getByLabel("Password").fill(required("E2E_OWNER_PASSWORD"));
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

/** Every violation, named with the colours or the element, so a failure is actionable as printed. */
function describe(violations: Awaited<ReturnType<AxeBuilder["analyze"]>>["violations"]): string {
  return violations
    .flatMap((violation) =>
      violation.nodes.map((node) => {
        const data = node.any[0]?.data as Record<string, unknown> | undefined;
        const detail =
          violation.id === "color-contrast" && data
            ? `fg=${String(data.fgColor)} bg=${String(data.bgColor)} ratio=${String(data.contrastRatio)}`
            : (node.any[0]?.message ?? "");
        return `  ${violation.id} [${violation.impact}] ${detail}\n    ${node.html.slice(0, 160)}`;
      }),
    )
    .join("\n");
}

for (const theme of ["light", "dark"] as const) {
  test(`the signed-in application meets WCAG 2.1 AA in the ${theme} theme`, async ({ browser }) => {
    test.slow();
    const context = await browser.newContext({
      viewport: { width: 1440, height: 900 },
      colorScheme: theme,
    });
    // The theme provider reads this before first paint, so the run never measures the wrong palette.
    await context.addInitScript((value) => {
      try {
        localStorage.setItem("wa.theme", value);
      } catch {
        /* a browser with storage blocked still falls back to the media query above */
      }
    }, theme);

    const page = await context.newPage();
    await signIn(page);

    const failures: string[] = [];
    for (const route of ROUTES) {
      await page.goto(route, { waitUntil: "networkidle" });
      const { violations } = await new AxeBuilder({ page }).withTags([...TAGS]).analyze();
      if (violations.length > 0) failures.push(`${route}:\n${describe(violations)}`);
    }

    expect(failures.join("\n\n"), `WCAG 2.1 AA violations (${theme})`).toBe("");
    await context.close();
  });
}

test("the application meets WCAG 2.1 AA at phone width", async ({ browser }) => {
  test.slow();
  // A phone reflows into sheets and stacked rows that the desktop layout never renders, so the
  // desktop pass does not cover them.
  const context = await browser.newContext({ viewport: { width: 375, height: 812 } });
  const page = await context.newPage();
  await signIn(page);

  const failures: string[] = [];
  for (const route of ROUTES) {
    await page.goto(route, { waitUntil: "networkidle" });
    const { violations } = await new AxeBuilder({ page }).withTags([...TAGS]).analyze();
    if (violations.length > 0) failures.push(`${route}:\n${describe(violations)}`);
  }

  expect(failures.join("\n\n"), "WCAG 2.1 AA violations (375px)").toBe("");
  await context.close();
});

test("the sign-in screen meets WCAG 2.1 AA before anyone is signed in", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  const { violations } = await new AxeBuilder({ page }).withTags([...TAGS]).analyze();
  expect(describe(violations), "WCAG 2.1 AA violations (sign-in)").toBe("");
});
