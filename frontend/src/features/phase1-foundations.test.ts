import { describe, expect, it } from "vitest";

import { navItems, visibleNavItems } from "@/components/layout/navigation";
import { OPERATIONS_SECTIONS } from "@/features/operations/sections";
import { REACTIVATION_SECTIONS } from "@/features/reactivation/sections";

describe("Phase 1 information architecture", () => {
  it("keeps the business workspace in the planned order", () => {
    expect(navItems.filter((item) => item.group === "Workspace").map((item) => item.label)).toEqual([
      "Dashboard", "Inbox", "Campaigns", "Broadcasts", "Templates", "Contacts", "Segments", "Automation", "Analytics", "Reactivation",
    ]);
  });

  it("keeps technical controls out of the business workspace", () => {
    expect(navItems.find((item) => item.label === "Operations")?.group).toBe("Platform");
    expect(navItems.find((item) => item.label === "Admin")?.group).toBe("Platform");
  });

  it("does not expose permission-gated modules without an entitlement", () => {
    expect(visibleNavItems(() => false).map((item) => item.label)).toEqual(["Dashboard"]);
  });
});

describe("Phase 1 foundation boundaries", () => {
  it("maps every operations surface to an existing permission", () => {
    expect(OPERATIONS_SECTIONS.every((section) => section.permission.length > 0)).toBe(true);
    expect(OPERATIONS_SECTIONS.map((section) => section.key)).toEqual([
      "overview", "jobs", "queues", "health", "logs", "api", "webhooks",
    ]);
  });

  it("labels reactivation foundations honestly while connecting reusable modules", () => {
    expect(REACTIVATION_SECTIONS.filter((section) => section.phase === "Foundation").length).toBeGreaterThan(0);
    expect(REACTIVATION_SECTIONS.filter((section) => section.phase === "Connected").map((section) => section.key)).toEqual([
      "pipeline", "documents", "reports",
    ]);
  });
});
