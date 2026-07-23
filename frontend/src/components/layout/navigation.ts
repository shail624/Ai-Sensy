import { ADMIN_PERMISSIONS } from "@/features/admin/sections";
import { SETTINGS_PERMISSIONS } from "@/features/settings/sections";

export interface NavItem {
  label: string;
  path: string;
  /** When false, the module is not built yet and routes to a "Coming soon" placeholder. */
  available: boolean;
  /** Short glyph for the collapsed sidebar rail (the foundation ships without an icon library). */
  glyph: string;
  /** Permission required to see this destination; omitted = visible to every signed-in user. */
  permission?: string;
  /**
   * Any one of these is enough. For a destination that aggregates several areas — Administration
   * covers users, roles, API keys and audit, each with its own permission — a single required
   * code would hide the whole section from someone entitled to part of it.
   */
  anyPermission?: string[];
}

function isVisible(item: NavItem, hasPermission: (code: string) => boolean): boolean {
  if (item.anyPermission) return item.anyPermission.some(hasPermission);
  return !item.permission || hasPermission(item.permission);
}

/** The destinations a user may actually reach, given their `MeResponse.permissions`. */
export function visibleNavItems(hasPermission: (code: string) => boolean): NavItem[] {
  return navItems.filter((item) => isVisible(item, hasPermission));
}

/** Single source of truth for primary navigation — shared by the sidebar and the dashboard cards. */
export const navItems: NavItem[] = [
  { label: "Dashboard", path: "/", available: true, glyph: "D" },
  { label: "Contacts", path: "/contacts", available: true, glyph: "C", permission: "contacts:read" },
  { label: "Segments", path: "/segments", available: true, glyph: "Sg", permission: "segments:read" },
  { label: "Pipelines", path: "/pipelines", available: true, glyph: "Pl", permission: "contacts:read" },
  { label: "Tasks", path: "/tasks", available: true, glyph: "Tk", permission: "tasks:read" },
  { label: "Inbox", path: "/inbox", available: true, glyph: "I", permission: "inbox:read" },
  { label: "Campaigns", path: "/campaigns", available: true, glyph: "Ca", permission: "campaigns:read" },
  { label: "Templates", path: "/templates", available: true, glyph: "T", permission: "templates:read" },
  { label: "Media", path: "/media", available: true, glyph: "M", permission: "media:read" },
  { label: "Analytics", path: "/analytics", available: true, glyph: "A", permission: "analytics:read" },
  { label: "WhatsApp", path: "/channels", available: true, glyph: "Wa", permission: "waba:read" },
  { label: "Operations", path: "/operations", available: true, glyph: "Op", permission: "system:read" },
  { label: "Admin", path: "/admin", available: true, glyph: "Ad", anyPermission: ADMIN_PERMISSIONS },
  { label: "Settings", path: "/settings", available: true, glyph: "S", anyPermission: SETTINGS_PERMISSIONS },
];
