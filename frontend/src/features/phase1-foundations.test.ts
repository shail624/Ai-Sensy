import { describe, expect, it } from "vitest";

import {
  EXCLUDED_NAVIGATION_TERMS,
  isPermittedNavItem,
  navItems,
  primaryNavItems,
  secondaryNavGroups,
  visibleCreateActions,
  visibleNavItems,
} from "@/components/layout/navigation";
import { OPERATIONS_SECTIONS } from "@/features/operations/sections";
import { REACTIVATION_SECTIONS } from "@/features/reactivation/sections";

describe("Phase 1 information architecture", () => {
  it("keeps the business workspace in the planned order", () => {
    expect(navItems.filter((item) => item.group === "Workspace").map((item) => item.label)).toEqual([
      "Dashboard", "Live Chat", "Campaigns", "Broadcasts", "Templates", "Contacts", "Segments", "Automation", "Analytics", "Reactivation",
    ]);
  });

  it("keeps technical controls out of the business workspace", () => {
    expect(navItems.find((item) => item.label === "Operations")?.group).toBe("Platform");
    expect(navItems.find((item) => item.label === "Admin")?.group).toBe("Platform");
  });

  it("keeps the default sidebar focused without removing entitled destinations", () => {
    expect(primaryNavItems(() => true).map((item) => item.label)).toEqual([
      "Dashboard", "Live Chat", "Contacts", "Campaigns", "Templates", "Analytics",
    ]);
    const secondary = secondaryNavGroups(() => true).flatMap((group) => group.items);
    expect(secondary.map((item) => item.label)).toContain("Media");
    expect(secondary.map((item) => item.label)).toContain("Automation");
    expect(secondary.map((item) => item.label)).toContain("Settings");
  });

  it("does not expose permission-gated modules without an entitlement", () => {
    expect(visibleNavItems(() => false).map((item) => item.label)).toEqual(["Dashboard"]);
  });

  it("permanently rejects excluded product concepts from navigation", () => {
    expect(navItems.every(isPermittedNavItem)).toBe(true);
    const catalog = navItems
      .map((item) => `${item.label} ${item.path} ${item.description}`)
      .join(" ")
      .toLocaleLowerCase();
    for (const term of EXCLUDED_NAVIGATION_TERMS) expect(catalog).not.toContain(term);
  });

  it("labels approved incomplete routes honestly instead of inventing capability", () => {
    expect(navItems.find((item) => item.path === "/reactivation")?.maturity).toBe("foundation");
    expect(navItems.find((item) => item.path === "/automation")?.maturity).toBe("foundation");
    expect(navItems.find((item) => item.path === "/scan")?.maturity).toBe("future");
  });

  it("shares permission-scoped create actions with the header and command palette", () => {
    const campaignWriter = (code: string) => code === "campaigns:write";
    expect(visibleCreateActions(campaignWriter).map((action) => action.path)).toEqual([
      "/campaigns/new",
    ]);
    expect(visibleCreateActions(() => false)).toEqual([]);
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
