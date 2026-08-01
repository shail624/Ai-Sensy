import { expect, test } from "@playwright/test";

function required(name: string): string {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}

test("owner imports and finds a contact through the deployed stack", async ({ page }) => {
  const ownerEmail = required("E2E_OWNER_EMAIL");
  const ownerPassword = required("E2E_OWNER_PASSWORD");
  // Keep the search text alphabetic: the existing contacts UI intentionally routes any query
  // containing digits to the phone-number field (buildRules.ts), not the name field.
  const contactName = "Release Gate Contact";
  const serverErrors: string[] = [];
  page.on("response", (response) => {
    if (response.status() >= 500) serverErrors.push(`${response.status()} ${response.url()}`);
  });

  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByLabel("Email").fill(ownerEmail);
  await page.getByLabel("Password").fill(ownerPassword);
  await page.getByRole("button", { name: "Sign in" }).click();

  await page.getByRole("link", { name: "Contacts", exact: true }).first().click();
  await expect(page.getByRole("heading", { name: "Contacts" })).toBeVisible();
  await page.getByRole("button", { name: "Import", exact: true }).click();
  await page.getByLabel("Choose a CSV or Excel file").setInputFiles({
    name: "release-gate-contact.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(`phone_e164,full_name\n+14155550123,${contactName}\n`, "utf8"),
  });

  await expect(page.getByText("2 columns", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("radio", { name: "Skip duplicates", exact: false })).toBeChecked();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("1", { exact: true }).first()).toBeVisible();
  await page.getByRole("button", { name: "Start import" }).click();

  await expect(page.getByText("Imported", { exact: true })).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("1 contacts", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Done" }).click();

  await page.getByLabel("Search contacts").fill(contactName);
  const contact = page.getByRole("link", { name: contactName, exact: true });
  await expect(contact).toBeVisible();
  await contact.click();
  await expect(page.getByText(contactName, { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("tab", { name: "KYC", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "SIM", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Tasks", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "AI Assistant", exact: true })).toBeVisible();

  // Product release evidence: engagement, reactivation, automation, and scan surfaces must be reachable through
  // the same production edge, authenticated shell, RBAC policy, and API contract.
  await page.goto("/broadcasts");
  await expect(page.getByRole("heading", { name: "Broadcast Center" })).toBeVisible();
  await expect(page.getByText("One campaign engine", { exact: true })).toBeVisible();

  await page.goto("/analytics");
  await expect(page.getByRole("heading", { name: "Analytics", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Engagement funnel" })).toBeVisible();

  await page.goto("/reactivation");
  await expect(page.getByRole("heading", { name: "Reactivation", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "One governed customer journey" })).toBeVisible();

  await page.goto("/automation");
  await expect(page.getByRole("heading", { name: "Automation", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "New automation" }).click();
  const automationDialog = page.getByRole("dialog", { name: "New automation" });
  await automationDialog.getByLabel("Name").fill("Release Gate Automation");
  await automationDialog.getByLabel("Description").fill("Deployed versioned authoring proof");
  await automationDialog.getByRole("button", { name: "Create draft" }).click();
  await expect(page.getByRole("button", { name: "Trigger", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Trigger", exact: true }).click();
  await page.getByRole("button", { name: "Notification", exact: true }).click();
  await page.getByRole("button", { name: "Save draft" }).click();
  await expect(page.getByText("Draft saved safely.", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Publish", exact: true }).click();
  await expect(page.getByText("Active version 1", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Run test" }).click();
  const testDialog = page.getByRole("dialog", { name: "Test automation" });
  await expect(testDialog.getByText("nothing is sent or changed", { exact: false })).toBeVisible();
  await testDialog.getByRole("button", { name: "Run safe test" }).click();
  await expect(page.getByText("Simulation complete. No live effect was applied.")).toBeVisible({
    timeout: 30_000,
  });

  const automationUrl = page.url();
  await page.goto("/contacts");
  await page.getByRole("button", { name: "Import", exact: true }).click();
  await page.getByLabel("Choose a CSV or Excel file").setInputFiles({
    name: "release-gate-trigger.csv",
    mimeType: "text/csv",
    buffer: Buffer.from(
      "phone_e164,full_name\n+14155550124,Automation Receipt Contact\n",
      "utf8",
    ),
  });
  await expect(page.getByText("2 columns", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Start import" }).click();
  await expect(page.getByText("Imported", { exact: true })).toBeVisible({ timeout: 60_000 });
  await page.getByRole("button", { name: "Done" }).click();
  await page.goto(automationUrl);
  await expect(page.getByRole("heading", { name: "Trigger receipts" })).toBeVisible();
  await expect(page.getByText("contact.created", { exact: true })).toBeVisible();
  await expect(page.getByText("Evidence only. No action executed.")).toBeVisible();

  await page.goto("/scan");
  await expect(page.getByRole("heading", { name: "Scan Studio", exact: true })).toBeVisible();
  await expect(page.getByText("Architecture boundary enforced", { exact: true })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/scan");
  await expect(page.getByRole("heading", { name: "Scan Studio", exact: true })).toBeVisible();
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(hasHorizontalOverflow).toBe(false);
  expect(serverErrors).toEqual([]);
});
