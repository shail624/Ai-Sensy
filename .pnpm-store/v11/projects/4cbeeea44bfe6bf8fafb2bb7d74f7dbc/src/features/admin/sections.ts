export interface AdminSection {
  key: string;
  label: string;
  path: string;
  /** The permission the API enforces for this section's reads (Doc 04 §12/§22). */
  permission: string;
  description: string;
}

/**
 * The administration areas, each gated by the permission its own endpoints enforce.
 *
 * Kept as data in one place so the sub-navigation, the route guards and the "which areas can this
 * person reach" question all read the same list — an admin who holds only `audit:read` sees the
 * Audit tab and nothing else, rather than a row of tabs that 403 on arrival.
 */
export const ADMIN_SECTIONS: AdminSection[] = [
  {
    key: "users",
    label: "Users",
    path: "/admin/users",
    permission: "users:read",
    description: "Accounts, their roles, and whether they can sign in.",
  },
  {
    key: "roles",
    label: "Roles & permissions",
    path: "/admin/roles",
    permission: "roles:read",
    description: "What each role may do, and who holds it.",
  },
  {
    key: "permissions",
    label: "Permissions",
    path: "/admin/permissions",
    permission: "roles:read",
    description: "Read-only catalog of capabilities enforced by the platform.",
  },
  {
    key: "api-keys",
    label: "API keys",
    path: "/admin/api-keys",
    permission: "apikeys:manage",
    description: "Credentials for integrations that call this platform.",
  },
  {
    key: "audit",
    label: "Audit log",
    path: "/admin/audit",
    permission: "audit:read",
    description: "Who did what, to which record, and when.",
  },
];

/** Any one of these is enough to reach the administration area at all. */
export const ADMIN_PERMISSIONS: string[] = ADMIN_SECTIONS.map((section) => section.permission);
