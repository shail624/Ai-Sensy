import {
  BarChart3,
  Bot,
  Contact,
  Code2,
  Download,
  History,
  Inbox,
  LayoutDashboard,
  ListChecks,
  type LucideIcon,
  Megaphone,
  MessageSquareText,
  RadioTower,
  Image,
  Settings,
  Shield,
  SlidersHorizontal,
  Sparkles,
  Tag,
  ScanSearch,
  Users,
  Workflow,
} from "lucide-react";

import { ADMIN_PERMISSIONS, ADMIN_SECTIONS } from "@/features/admin/sections";
import { SETTINGS_PERMISSIONS, SETTINGS_SECTIONS } from "@/features/settings/sections";

export interface NavItem {
  label: string;
  /** Familiar, short caption for the compact daily-work rail. */
  railLabel?: string;
  path: string;
  /** Legacy catalogue flag retained while all registered destinations are real, routed surfaces. */
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
  /** Honest maturity marker for approved routes whose dedicated domain capability is not complete. */
  maturity?: "foundation" | "future";
}

export interface CreateAction {
  label: string;
  description: string;
  path: string;
  icon: LucideIcon;
  permission: string;
  keywords: string[];
}

export const EXCLUDED_NAVIGATION_TERMS = [
  "ads manager",
  "meta ads",
  "payments",
  "billing",
  "subscriptions",
  "marketplace",
  "multi-project",
  "public signup",
  "reseller",
  "catalog",
  "cart",
  "checkout",
  "orders",
  "refunds",
  "commerce",
] as const;

/** Permanent CORE-01 scope guard used by navigation tests and runtime filtering. */
export function isPermittedNavItem(item: Pick<NavItem, "label" | "path" | "description">): boolean {
  const searchable = `${item.label} ${item.path} ${item.description}`.toLocaleLowerCase();
  return !EXCLUDED_NAVIGATION_TERMS.some((term) => searchable.includes(term));
}

function isVisible(item: NavItem, hasPermission: (code: string) => boolean): boolean {
  if (item.anyPermission) return item.anyPermission.some(hasPermission);
  return !item.permission || hasPermission(item.permission);
}

/** The destinations a user may actually reach, given their `MeResponse.permissions`. */
export function visibleNavItems(hasPermission: (code: string) => boolean): NavItem[] {
  return navItems.filter((item) => isPermittedNavItem(item) && isVisible(item, hasPermission));
}

export const createActions: CreateAction[] = [
  {
    label: "Campaign",
    description: "Build a governed WhatsApp broadcast",
    path: "/campaigns/new",
    icon: Megaphone,
    permission: "campaigns:write",
    keywords: ["broadcast", "send", "message"],
  },
  {
    label: "Template",
    description: "Create a WhatsApp message template",
    path: "/templates/new",
    icon: MessageSquareText,
    permission: "templates:write",
    keywords: ["message", "meta", "author"],
  },
  {
    label: "Import contacts",
    description: "Upload a CSV or Excel contact file",
    path: "/contacts?import=1",
    icon: Contact,
    permission: "contacts:import",
    keywords: ["upload", "csv", "excel"],
  },
];

export function visibleCreateActions(hasPermission: (code: string) => boolean): CreateAction[] {
  return createActions.filter((action) => hasPermission(action.permission));
}

/**
 * Keep the AiSensy-style daily workspace visible in the rail. Configuration and the product's
 * additional Vi operations remain available through the Manage section and workspace search.
 */
export const PRIMARY_NAV_PATHS = [
  "/",
  "/inbox",
  "/chat-history",
  "/contacts",
  "/segments",
  "/campaigns",
  "/automation",
  "/operations/api",
] as const;

export function primaryNavItems(hasPermission: (code: string) => boolean): NavItem[] {
  const visible = new Map(visibleNavItems(hasPermission).map((item) => [item.path, item]));
  return PRIMARY_NAV_PATHS.flatMap((path) => {
    const item = visible.get(path);
    return item ? [item] : [];
  });
}

export function secondaryNavGroups(
  hasPermission: (code: string) => boolean,
): { group: string; items: NavItem[] }[] {
  const primary = new Set<string>(PRIMARY_NAV_PATHS);
  return groupedNavItems(hasPermission)
    .map(({ group, items }) => ({ group, items: items.filter((item) => !primary.has(item.path)) }))
    .filter(({ items }) => items.length > 0);
}

/** Direct entry points to existing settings; no duplicate services or placeholder destinations. */
export function manageNavGroups(
  hasPermission: (code: string) => boolean,
): { group: string; items: NavItem[] }[] {
  const visible = visibleNavItems(hasPermission);
  const byPath = new Map(visible.map((item) => [item.path, item]));
  const destination = (path: string, label?: string): NavItem[] => {
    const item = byPath.get(path);
    return item ? [{ ...item, label: label ?? item.label }] : [];
  };
  const setting = (key: string): NavItem[] => {
    const section = SETTINGS_SECTIONS.find((item) => item.key === key);
    return section && hasPermission(section.permission) ? [{
      ...section, available: true, glyph: "S",
      icon: key === "tags" ? Tag : key === "canned-messages" ? MessageSquareText : key === "user-attributes" ? SlidersHorizontal : Settings,
      group: "Manage",
    }] : [];
  };
  const team = ADMIN_SECTIONS.find((item) => item.key === "users")!;
  const manage = [
    ...destination("/templates", "Template Message"),
    ...(hasPermission("settings:read") ? [
      { label: "Opt-in Management", path: "/settings/application#consent", available: true,
        glyph: "O", icon: Shield, group: "Manage", permission: "settings:read",
        description: "Configure opt-in and opt-out keyword handling." },
      { label: "Live Chat Settings", path: "/settings/application#inbox-policy", available: true,
        glyph: "L", icon: Inbox, group: "Manage", permission: "settings:read",
        description: "Routing, working hours, automatic replies and resolution." },
    ] : []),
    ...setting("user-attributes"),
    ...setting("canned-messages"),
    ...(hasPermission(team.permission) ? [{
      ...team, label: "Team", available: true, glyph: "T", icon: Users, group: "Manage",
    }] : []),
    ...setting("tags"),
    ...destination("/analytics"),
  ];
  const covered = new Set(["/templates", "/analytics", "/settings", "/admin"]);
  const additional = secondaryNavGroups(hasPermission)
    .map((group) => ({ ...group, items: group.items.filter((item) => !covered.has(item.path)) }))
    .filter((group) => group.items.length > 0);
  const configuration = [
    ...["organization", "application", "flags", "preferences"].flatMap(setting),
    ...ADMIN_SECTIONS.filter((section) => section.key !== "users" && hasPermission(section.permission))
      .map((section) => ({ ...section,
        description: section.key === "permissions" ? "Review the capabilities enforced by the platform." : section.description,
        available: true, glyph: "A", icon: Shield, group: "Platform" })),
  ];
  return [
    ...(manage.length ? [{ group: "Manage", items: manage }] : []),
    ...additional,
    ...(configuration.length ? [{ group: "Configuration", items: configuration }] : []),
  ];
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
    group: "Workspace", description: "Your executive workspace, priorities and messaging performance.",
  },
  {
    label: "Live Chat", path: "/inbox", available: true, glyph: "L", icon: Inbox,
    group: "Workspace", permission: "inbox:read",
    description: "One shared team inbox for every conversation.",
  },
  {
    label: "Chat History", railLabel: "History", path: "/chat-history", available: true, glyph: "Ch", icon: History,
    group: "Workspace", permission: "inbox:read",
    description: "Read-only conversation and message history, separate from live triage.",
  },
  {
    label: "Campaigns", path: "/campaigns", available: true, glyph: "Ca", icon: Megaphone,
    group: "Workspace", permission: "campaigns:read",
    description: "Build, schedule and monitor WhatsApp broadcasts.",
  },
  {
    label: "Broadcasts", path: "/broadcasts", available: true, glyph: "B", icon: RadioTower,
    group: "Workspace", permission: "campaigns:read",
    description: "Launch governed broadcasts through the campaign engine.",
  },
  {
    label: "Templates", path: "/templates", available: true, glyph: "T", icon: MessageSquareText,
    group: "Workspace", permission: "templates:read",
    description: "Author and sync WhatsApp message templates.",
  },
  {
    label: "Contacts", path: "/contacts", available: true, glyph: "C", icon: Contact,
    group: "Workspace", permission: "contacts:read",
    description: "Manage customers, tags and custom attributes.",
  },
  {
    label: "Segments", path: "/segments", available: true, glyph: "Sg", icon: Users,
    group: "Workspace", permission: "segments:read",
    description: "Build dynamic audiences from live contact rules.",
  },
  {
    label: "Automation", railLabel: "Flows", path: "/automation", available: true, glyph: "Au", icon: Bot,
    group: "Workspace", permission: "automations:read",
    description: "Build and publish governed, versioned workflow definitions.",
    maturity: "foundation",
  },
  {
    label: "Analytics", path: "/analytics", available: true, glyph: "A", icon: BarChart3,
    group: "Workspace", permission: "analytics:read",
    description: "Delivery, campaign and conversation reporting.",
  },
  {
    label: "Reactivation", path: "/reactivation", available: true, glyph: "R", icon: Sparkles,
    group: "Workspace", permission: "reactivation:read",
    description: "Governed Vi case pipeline, evidence and follow-up work.",
  },
  {
    label: "Tasks", path: "/tasks", available: true, glyph: "Tk", icon: ListChecks,
    group: "Tools", permission: "tasks:read",
    description: "Assign and track customer follow-up work.",
  },
  {
    label: "Download Center", path: "/downloads", available: true, glyph: "Dl", icon: Download,
    group: "Tools", anyPermission: [
      "contacts:export",
      "analytics:export",
      "inbox:export",
      "campaigns:export",
    ],
    description: "Track and securely download generated exports, reports and chat transcripts.",
  },
  {
    label: "Media", path: "/media", available: true, glyph: "M", icon: Image,
    group: "Tools", permission: "media:read",
    description: "Store and reuse images, documents and video.",
  },
  {
    label: "Pipelines", path: "/pipelines", available: true, glyph: "Pl", icon: Workflow,
    group: "Tools", permission: "contacts:read",
    description: "Track leads through your qualification stages.",
  },
  {
    label: "Scan Studio", path: "/scan", available: true, glyph: "Sc", icon: ScanSearch,
    group: "Tools", permission: "contacts:read",
    description: "Future compliant number-scan workspace and CRM hand-off.",
    maturity: "future",
  },
  {
    label: "WhatsApp", path: "/channels", available: true, glyph: "Wa", icon: MessageSquareText,
    group: "Tools", permission: "waba:read",
    description: "Connect business accounts and phone numbers.",
  },
  {
    label: "Operations", path: "/operations", available: true, glyph: "Op", icon: SlidersHorizontal,
    group: "Platform", anyPermission: ["system:read", "apikeys:manage", "waba:read"],
    description: "System health, queues, jobs, APIs and webhook operations.",
  },
  {
    label: "Developer", path: "/operations/api", available: true, glyph: "Dv", icon: Code2,
    group: "Platform", permission: "apikeys:manage",
    description: "Manage project API credentials from a direct developer entry point.",
  },
  {
    label: "Admin", path: "/admin", available: true, glyph: "Ad", icon: Shield,
    group: "Platform", anyPermission: ADMIN_PERMISSIONS,
    description: "Users, roles, API keys and the audit log.",
  },
  {
    label: "Settings", path: "/settings", available: true, glyph: "S", icon: Settings,
    group: "Platform", anyPermission: SETTINGS_PERMISSIONS,
    description: "Organization profile and feature flags.",
  },
];
