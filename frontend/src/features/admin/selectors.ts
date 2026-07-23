import type {
  AuditEntry,
  AuditListQuery,
  Permission,
  Role,
  User,
  UserListQuery,
  UserSort,
} from "@/features/admin/types";
import { actionEntity } from "@/features/admin/types";

/** Rows per page for the client-side lists (see `api.ts` for why paging lives here). */
export const PAGE_SIZE = 25;

export interface Paged<T> {
  rows: T[];
  total: number;
  totalPages: number;
  /** Clamped: a filter change that shortens the list must not strand the user on a dead page. */
  page: number;
}

/** Filter → sort → slice, shared by every admin list so they page identically. */
export function paginate<T>(matched: T[], page: number): Paged<T> {
  const totalPages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
  const current = Math.min(Math.max(1, page), totalPages);
  const start = (current - 1) * PAGE_SIZE;
  return {
    rows: matched.slice(start, start + PAGE_SIZE),
    total: matched.length,
    totalPages,
    page: current,
  };
}

// --- Users --------------------------------------------------------------------------------------

const USER_COMPARATORS: Record<UserSort, (a: User, b: User) => number> = {
  name: (a, b) => a.full_name.localeCompare(b.full_name),
  "-name": (a, b) => b.full_name.localeCompare(a.full_name),
  created_at: (a, b) => Date.parse(a.created_at) - Date.parse(b.created_at),
  "-created_at": (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  // Never signed in sorts last: absent is not "longest ago", it is a different thing entirely.
  "-last_login_at": (a, b) =>
    (b.last_login_at ? Date.parse(b.last_login_at) : -Infinity) -
    (a.last_login_at ? Date.parse(a.last_login_at) : -Infinity),
};

/** Matches name or email — the two things an administrator has when looking for a person. */
export function matchesUser(user: User, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return (
    user.full_name.toLowerCase().includes(needle) || user.email.toLowerCase().includes(needle)
  );
}

export function filterUsers(users: User[], query: UserListQuery): User[] {
  return users.filter(
    (user) =>
      matchesUser(user, query.q) &&
      (query.status === "" ||
        (query.status === "active" ? user.is_active : !user.is_active)) &&
      (query.role === "" || user.roles.includes(query.role)),
  );
}

export function selectUserPage(users: User[], query: UserListQuery): Paged<User> {
  const matched = [...filterUsers(users, query)].sort(USER_COMPARATORS[query.sort]);
  return paginate(matched, query.page);
}

export interface UserSummary {
  total: number;
  active: number;
  disabled: number;
  neverSignedIn: number;
}

export function userSummary(users: User[]): UserSummary {
  return {
    total: users.length,
    active: users.filter((user) => user.is_active).length,
    disabled: users.filter((user) => !user.is_active).length,
    neverSignedIn: users.filter((user) => !user.last_login_at).length,
  };
}

/**
 * Whether the signed-in administrator may disable this account.
 *
 * Locking yourself out is the one mistake this screen can make irreversibly from the browser, so
 * an admin is never offered the control on their own row. The server has its own guards; this
 * removes the foot-gun rather than relying on catching it afterwards.
 */
export function canToggleActive(user: User, currentUserId: string | undefined): boolean {
  return user.id !== currentUserId;
}

// --- Roles & permissions -------------------------------------------------------------------------

export interface PermissionGroup {
  resource: string;
  permissions: Permission[];
}

/**
 * The catalog grouped by resource, in catalog order.
 *
 * The matrix is only readable if `contacts:*` sit together; the seed order already reflects how the
 * permissions were designed, so it is preserved rather than re-sorted alphabetically.
 */
export function groupPermissions(permissions: Permission[]): PermissionGroup[] {
  const groups: PermissionGroup[] = [];
  for (const permission of permissions) {
    const existing = groups.find((group) => group.resource === permission.resource);
    if (existing) existing.permissions.push(permission);
    else groups.push({ resource: permission.resource, permissions: [permission] });
  }
  return groups;
}

/** How many users hold each role, from the users already loaded. */
export function roleUsage(users: User[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const user of users) {
    for (const role of user.roles) counts[role] = (counts[role] ?? 0) + 1;
  }
  return counts;
}

/**
 * A role is deletable only when it is neither seeded nor in use — the same two conditions the
 * server enforces before answering 409.
 */
export function isRoleDeletable(role: Role, usage: Record<string, number>): boolean {
  return !role.is_system && (usage[role.name] ?? 0) === 0;
}

/** Roles sorted with the seeded ones first, so the shipped set reads as the baseline it is. */
export function sortRoles(roles: Role[]): Role[] {
  return [...roles].sort((a, b) => {
    if (a.is_system !== b.is_system) return a.is_system ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
}

// --- Audit ----------------------------------------------------------------------------------------

/** Matches the action, the actor, the entity type or the IP — whatever the reader has to go on. */
export function matchesAudit(entry: AuditEntry, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return [entry.action, entry.actor, entry.entity_type, entry.ip_address]
    .filter((value): value is string => typeof value === "string")
    .some((value) => value.toLowerCase().includes(needle));
}

export function filterAudit(entries: AuditEntry[], query: AuditListQuery): AuditEntry[] {
  return entries.filter(
    (entry) =>
      matchesAudit(entry, query.q) &&
      (query.action === "" || entry.action === query.action) &&
      (query.entity === "" || actionEntity(entry.action) === query.entity) &&
      (query.actor === "" || entry.actor === query.actor),
  );
}

export function selectAuditPage(entries: AuditEntry[], query: AuditListQuery): Paged<AuditEntry> {
  return paginate(filterAudit(entries, query), query.page);
}

/**
 * Filter options derived from the entries actually loaded.
 *
 * The action vocabulary is large and grows with every module; offering the ~80 constants — most of
 * which this page will never show — would be a worse filter than offering exactly what is present.
 */
export function auditFacets(entries: AuditEntry[]): {
  actions: string[];
  entities: string[];
  actors: string[];
} {
  const actions = new Set<string>();
  const entities = new Set<string>();
  const actors = new Set<string>();
  for (const entry of entries) {
    actions.add(entry.action);
    entities.add(actionEntity(entry.action));
    if (entry.actor) actors.add(entry.actor);
  }
  return {
    actions: [...actions].sort(),
    entities: [...entities].sort(),
    actors: [...actors].sort(),
  };
}

export interface AuditChange {
  field: string;
  before: unknown;
  after: unknown;
}

/**
 * The fields an entry actually changed, from its `before`/`after` snapshots.
 *
 * Both sides are free-form objects on the wire, and either may be absent — a creation has no
 * `before`, a deletion no `after` — so the union of their keys is what makes a diff readable.
 */
export function auditChanges(entry: AuditEntry): AuditChange[] {
  const before = (entry.before ?? {}) as Record<string, unknown>;
  const after = (entry.after ?? {}) as Record<string, unknown>;
  const fields = [...new Set([...Object.keys(before), ...Object.keys(after)])].sort();
  return fields
    .map((field) => ({ field, before: before[field], after: after[field] }))
    .filter((change) => JSON.stringify(change.before) !== JSON.stringify(change.after));
}
