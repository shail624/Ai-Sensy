import {
  BarChart3,
  Contact,
  Inbox,
  LayoutDashboard,
  ListChecks,
  type LucideIcon,
  Megaphone,
  MessageSquareText,
  Image,
  Settings,
  Shield,
  SlidersHorizontal,
  Users,
  Workflow,
} from "lucide-react";

import { ADMIN_PERMISSIONS } from "@/features/admin/sections";
import { SETTINGS_PERMISSIONS } from "@/features/settings/sections";

export interface NavItem {
  label: string;
  path: string;
  /** When false, the module is not built yet and routes to a "Coming soon" placeholder. */
  available: boolean;
  /** Short glyph for accessibility fallbacks and the collapsed rail. */
  glyph: string;
  /** The icon rendered in the sidebar and on the dashboard cards. */
  icon: LucideIcon;
  /** One-line description shown on the dashboard module cards. */
  description: string;
  /** Sidebar grouping header — related destinations sit together (Doc 05 IA). */
  group: string;
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

/** Nav groups in display order, each with the visible items that belong to it. */
export function groupedNavItems(
  hasPermission: (code: string) => boolean,
): { group: string; items: NavItem[] }[] {
  const visible = visibleNavItems(hasPermission);
  const order: string[] = [];
  const byGroup = new Map<string, NavItem[]>();
  for (const item of visible) {
    if (!byGroup.has(item.group)) {
      byGroup.set(item.group, []);
      order.push(item.group);
    }
    byGroup.get(item.group)!.push(item);
  }
  return order.map((group) => ({ group, items: byGroup.get(group)! }));
}

/** Single source of truth for primary navigation — shared by the sidebar and the dashboard cards. */
export const navItems: NavItem[] = [
  {
    label: "Dashboard", path: "/", available: true, glyph: "D", icon: LayoutDashboard,
    group: "Overview", description: "Your workspace at a glance and today's follow-ups.",
  },
  {
    label: "Contacts", path: "/contacts", available: true, glyph: "C", icon: Contact,
    group: "Audience", permission: "contacts:read",
    description: "Manage customers, tags and custom attributes.",
  },
  {
    label: "Segments", path: "/segments", available: true, glyph: "Sg", icon: Users,
    group: "Audience", permission: "segments:read",
    description: "Build dynamic audiences from live contact rules.",
  },
  {
    label: "Pipelines", path: "/pipelines", available: true, glyph: "Pl", icon: Workflow,
    group: "Audience", permission: "contacts:read",
    description: "Track leads through your qualification stages.",
  },
  {
    label: "Inbox", path: "/inbox", available: true, glyph: "I", icon: Inbox,
    group: "Engage", permission: "inbox:read",
    description: "One shared team inbox for every conversation.",
  },
  {
    label: "Campaigns", path: "/campaigns", available: true, glyph: "Ca", icon: Megaphone,
    group: "Engage", permission: "campaigns:read",
    description: "Broadcast approved templates to your audiences.",
  },
  {
    label: "Templates", path: "/templates", available: true, glyph: "T", icon: MessageSquareText,
    group: "Engage", permission: "templates:read",
    description: "Author and sync WhatsApp message templates.",
  },
  {
    label: "Tasks", path: "/tasks", available: true, glyph: "Tk", icon: ListChecks,
    group: "Engage", permission: "tasks:read",
    description: "Assign and track customer follow-up work.",
  },
  {
    label: "Media", path: "/media", available: true, glyph: "M", icon: Image,
    group: "Engage", permission: "media:read",
    description: "Store and reuse images, documents and video.",
  },
  {
    label: "Analytics", path: "/analytics", available: true, glyph: "A", icon: BarChart3,
    group: "Insights", permission: "analytics:read",
    description: "Delivery, campaign and conversation reporting.",
  },
  {
    label: "WhatsApp", path: "/channels", available: true, glyph: "Wa", icon: MessageSquareText,
    group: "Configure", permission: "waba:read",
    description: "Connect business accounts and phone numbers.",
  },
  {
    label: "Operations", path: "/operations", available: true, glyph: "Op", icon: SlidersHorizontal,
    group: "Configure", permission: "system:read",
    description: "Queues, workers and background job health.",
  },
  {
    label: "Admin", path: "/admin", available: true, glyph: "Ad", icon: Shield,
    group: "Configure", anyPermission: ADMIN_PERMISSIONS,
    description: "Users, roles, API keys and the audit log.",
  },
  {
    label: "Settings", path: "/settings", available: true, glyph: "S", icon: Settings,
    group: "Configure", anyPermission: SETTINGS_PERMISSIONS,
    description: "Organization profile and feature flags.",
  },
];
