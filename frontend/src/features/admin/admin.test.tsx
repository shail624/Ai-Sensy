import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { visibleNavItems } from "@/components/layout/navigation";
import { AdminPagination } from "@/features/admin/AdminPagination";
import { ApiKeyStateChip, StatusChip } from "@/features/admin/AdminBadges";
import { AuditDetailDialog } from "@/features/admin/AuditDetailDialog";
import { PermissionMatrix } from "@/features/admin/PermissionMatrix";
import {
  auditChanges,
  auditFacets,
  canToggleActive,
  filterAudit,
  filterUsers,
  groupPermissions,
  isRoleDeletable,
  matchesUser,
  PAGE_SIZE,
  paginate,
  roleUsage,
  selectUserPage,
  sortRoles,
  userSummary,
} from "@/features/admin/selectors";
import { UsersPanel } from "@/features/admin/UsersPanel";
import type {
  ApiKey,
  AuditEntry,
  Permission,
  Role,
  User,
  UserListQuery,
} from "@/features/admin/types";
import {
  actionEntity,
  apiKeyState,
  DEFAULT_USER_QUERY,
  humanizeAction,
  isDisabled,
  isSecurityEvent,
} from "@/features/admin/types";

// --- Fixtures -----------------------------------------------------------------------------------

function userFixture(overrides: Partial<User> = {}): User {
  return {
    id: "u1",
    type: "user",
    email: "priya@example.com",
    full_name: "Priya S.",
    phone: null,
    avatar_url: null,
    timezone: "Asia/Kolkata",
    locale: "en",
    is_active: true,
    is_superuser: false,
    mfa_enabled: false,
    roles: ["agent"],
    last_login_at: "2026-07-22T09:00:00Z",
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    row_version: 2,
    ...overrides,
  };
}

function roleFixture(overrides: Partial<Role> = {}): Role {
  return {
    id: "r1",
    name: "agent",
    description: "Front-line support.",
    is_system: true,
    permissions: ["inbox:read", "inbox:write"],
    ...overrides,
  };
}

function permissionFixture(code: string, description?: string): Permission {
  const [resource = "", action = ""] = code.split(":");
  return { code, resource, action, description: description ?? null };
}

function keyFixture(overrides: Partial<ApiKey> = {}): ApiKey {
  return {
    id: "k1",
    type: "api_key",
    name: "billing-sync",
    key_prefix: "wa_live_ab12",
    scopes: ["contacts:read"],
    is_active: true,
    last_used_at: null,
    expires_at: null,
    revoked_at: null,
    created_at: "2026-07-01T10:00:00Z",
    ...overrides,
  };
}

function auditFixture(overrides: Partial<AuditEntry> = {}): AuditEntry {
  return {
    id: 1,
    action: "user.updated",
    actor_type: "user",
    actor: "priya@example.com",
    entity_type: "user",
    entity_id: 7,
    ip_address: "10.0.0.4",
    before: { full_name: "Priya", is_active: true },
    after: { full_name: "Priya S.", is_active: true },
    metadata: null,
    created_at: "2026-07-22T09:00:00Z",
    ...overrides,
  };
}

// --- Harness ------------------------------------------------------------------------------------

const permissions = {
  value: ["users:read", "users:manage", "roles:read", "roles:write", "apikeys:manage", "audit:read"],
};
const currentUserId = { value: "u-me" };

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: currentUserId.value, permissions: permissions.value, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.value.includes(code),
  }),
  useHasPermission: (code: string) => permissions.value.includes(code),
}));

/** Canned responses per path, so the real hooks and components run without a network. */
const responses: Record<string, unknown> = {};

vi.mock("@/lib/api/client", () => {
  const get = async (path: string) =>
    path in responses
      ? { data: responses[path] }
      : { error: new Error(`no stub for ${path}`) };
  const write = async () => ({ error: new Error("network disabled under test") });
  return {
    api: { GET: get, POST: write, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

function query(overrides: Partial<UserListQuery> = {}): UserListQuery {
  return { ...DEFAULT_USER_QUERY, ...overrides };
}

beforeEach(() => {
  permissions.value = [
    "users:read",
    "users:manage",
    "roles:read",
    "roles:write",
    "apikeys:manage",
    "audit:read",
  ];
  currentUserId.value = "u-me";
  for (const key of Object.keys(responses)) delete responses[key];
});

// --- Users --------------------------------------------------------------------------------------

describe("selectors — users", () => {
  const rows = [
    userFixture({ id: "a", full_name: "Anita", email: "anita@x.com", roles: ["agent"] }),
    userFixture({ id: "b", full_name: "Bala", email: "bala@x.com", roles: ["manager"], is_active: false }),
    userFixture({ id: "c", full_name: "Chitra", email: "chitra@x.com", roles: ["agent", "analyst"], last_login_at: null }),
  ];

  it("searches name and email", () => {
    expect(matchesUser(rows[0]!, "ANI")).toBe(true);
    expect(matchesUser(rows[0]!, "bala@")).toBe(false);
    expect(matchesUser(rows[0]!, "  ")).toBe(true);
  });

  it("filters by status and role", () => {
    expect(filterUsers(rows, query({ status: "inactive" })).map((r) => r.id)).toEqual(["b"]);
    expect(filterUsers(rows, query({ role: "agent" })).map((r) => r.id)).toEqual(["a", "c"]);
  });

  it("sorts users who have never signed in last, not first", () => {
    // Absent is not "longest ago" — a null last-login must not sort as the oldest date.
    const sorted = selectUserPage(rows, query({ sort: "-last_login_at" })).rows;
    expect(sorted[sorted.length - 1]?.id).toBe("c");
  });

  it("summarises the roster", () => {
    expect(userSummary(rows)).toEqual({ total: 3, active: 2, disabled: 1, neverSignedIn: 1 });
  });

  it("never lets an administrator disable their own account", () => {
    expect(canToggleActive(userFixture({ id: "u-me" }), "u-me")).toBe(false);
    expect(canToggleActive(userFixture({ id: "other" }), "u-me")).toBe(true);
  });

  it("reads disabled off the active flag", () => {
    expect(isDisabled(userFixture({ is_active: false }))).toBe(true);
    expect(isDisabled(userFixture())).toBe(false);
  });
});

describe("selectors — pagination", () => {
  it("clamps a page past the end and slices at the page size", () => {
    const many = Array.from({ length: PAGE_SIZE + 6 }, (_, index) => index);
    expect(paginate(many, 1).rows).toHaveLength(PAGE_SIZE);
    expect(paginate(many, 2).rows).toHaveLength(6);
    expect(paginate(many, 99).page).toBe(2);
    expect(paginate([], 3)).toMatchObject({ total: 0, totalPages: 1, page: 1 });
  });
});

// --- Roles & permissions --------------------------------------------------------------------------

describe("selectors — roles and permissions", () => {
  it("groups the catalog by resource in catalog order, not alphabetically", () => {
    const groups = groupPermissions([
      permissionFixture("users:read"),
      permissionFixture("contacts:read"),
      permissionFixture("users:write"),
    ]);
    expect(groups.map((group) => group.resource)).toEqual(["users", "contacts"]);
    expect(groups[0]?.permissions).toHaveLength(2);
  });

  it("counts how many users hold each role", () => {
    expect(
      roleUsage([
        userFixture({ roles: ["agent"] }),
        userFixture({ roles: ["agent", "analyst"] }),
      ]),
    ).toEqual({ agent: 2, analyst: 1 });
  });

  it("refuses to delete a system role or one still in use", () => {
    expect(isRoleDeletable(roleFixture({ is_system: true, name: "agent" }), {})).toBe(false);
    expect(isRoleDeletable(roleFixture({ is_system: false, name: "custom" }), { custom: 1 })).toBe(false);
    expect(isRoleDeletable(roleFixture({ is_system: false, name: "custom" }), {})).toBe(true);
  });

  it("lists system roles before custom ones", () => {
    const sorted = sortRoles([
      roleFixture({ id: "z", name: "zeta", is_system: false }),
      roleFixture({ id: "a", name: "admin", is_system: true }),
    ]);
    expect(sorted.map((role) => role.name)).toEqual(["admin", "zeta"]);
  });
});

describe("PermissionMatrix", () => {
  const catalog = [
    permissionFixture("contacts:read", "View contacts"),
    permissionFixture("contacts:write"),
    permissionFixture("inbox:read"),
  ];
  const roles = [
    roleFixture({ id: "sys", name: "agent", is_system: true, permissions: ["inbox:read"] }),
    roleFixture({ id: "cus", name: "custom", is_system: false, permissions: ["contacts:read"] }),
  ];

  it("marks which roles hold each permission", () => {
    withProviders(<PermissionMatrix permissions={catalog} roles={roles} />);
    expect(screen.getByLabelText("agent has inbox:read")).toBeInTheDocument();
    expect(screen.getByLabelText("agent does not have contacts:read")).toBeInTheDocument();
  });

  it("groups by resource and shows each permission's description", () => {
    withProviders(<PermissionMatrix permissions={catalog} roles={roles} />);
    expect(screen.getByText("contacts")).toBeInTheDocument();
    expect(screen.getByText("View contacts")).toBeInTheDocument();
  });

  it("makes only the edited custom role's column editable", () => {
    withProviders(
      <PermissionMatrix
        permissions={catalog}
        roles={roles}
        editingRoleId="cus"
        draft={["contacts:read"]}
        onToggle={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("contacts:read for custom")).toBeChecked();
    expect(screen.getByLabelText("contacts:write for custom")).not.toBeChecked();
    // The system role stays read-only even while another role is being edited.
    expect(screen.queryByLabelText("inbox:read for agent")).not.toBeInTheDocument();
  });

  it("never offers to edit a system role's own column", () => {
    withProviders(
      <PermissionMatrix
        permissions={catalog}
        roles={roles}
        editingRoleId="sys"
        draft={["inbox:read"]}
        onToggle={vi.fn()}
      />,
    );
    expect(screen.queryByRole("checkbox")).not.toBeInTheDocument();
  });

  it("grants or clears a whole resource group at once", () => {
    const onToggleResource = vi.fn();
    withProviders(
      <PermissionMatrix
        permissions={catalog}
        roles={roles}
        editingRoleId="cus"
        draft={["contacts:read"]}
        onToggle={vi.fn()}
        onToggleResource={onToggleResource}
      />,
    );
    fireEvent.click(screen.getAllByRole("button", { name: "Grant all" })[0]!);
    expect(onToggleResource).toHaveBeenCalledWith(["contacts:read", "contacts:write"], true);
  });

  it("explains that superusers bypass the matrix entirely", () => {
    withProviders(<PermissionMatrix permissions={catalog} roles={roles} />);
    expect(screen.getByText(/superuser bypasses every check/)).toBeInTheDocument();
  });
});

// --- API keys -------------------------------------------------------------------------------------

describe("apiKeyState", () => {
  const now = Date.parse("2026-07-23T00:00:00Z");

  it("reports an expired key as expired, not active", () => {
    // `is_active` is still true — nothing revoked it — but it can no longer be used.
    expect(apiKeyState(keyFixture({ expires_at: "2026-07-01T00:00:00Z" }), now)).toBe("expired");
  });

  it("treats revocation as final, whatever the expiry says", () => {
    expect(
      apiKeyState(keyFixture({ revoked_at: "2026-07-02T00:00:00Z", expires_at: "2027-01-01T00:00:00Z" }), now),
    ).toBe("revoked");
    expect(apiKeyState(keyFixture({ is_active: false }), now)).toBe("revoked");
  });

  it("reports a live, unexpired key as active", () => {
    expect(apiKeyState(keyFixture({ expires_at: "2027-01-01T00:00:00Z" }), now)).toBe("active");
    expect(apiKeyState(keyFixture(), now)).toBe("active");
  });
});

describe("AdminBadges", () => {
  it("labels account status", () => {
    withProviders(
      <>
        <StatusChip active />
        <StatusChip active={false} />
      </>,
    );
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Disabled")).toBeInTheDocument();
  });

  it("labels each key state", () => {
    withProviders(<ApiKeyStateChip state="expired" />);
    expect(screen.getByText("Expired")).toBeInTheDocument();
  });
});

// --- Audit ----------------------------------------------------------------------------------------

describe("audit helpers", () => {
  it("turns a dotted action code into a readable phrase", () => {
    expect(humanizeAction("user.login_failed")).toBe("Login failed");
    expect(humanizeAction("campaign.dispatched")).toBe("Dispatched");
    expect(actionEntity("api_key.created")).toBe("api_key");
  });

  it("flags the security-relevant failures", () => {
    expect(isSecurityEvent("user.login_failed")).toBe(true);
    expect(isSecurityEvent("user.token_reuse_detected")).toBe(true);
    expect(isSecurityEvent("user.login")).toBe(false);
  });

  it("diffs only the fields that actually changed", () => {
    const changes = auditChanges(auditFixture());
    expect(changes).toEqual([{ field: "full_name", before: "Priya", after: "Priya S." }]);
  });

  it("treats a creation as all-new and a deletion as all-removed", () => {
    expect(auditChanges(auditFixture({ before: null, after: { name: "x" } }))).toEqual([
      { field: "name", before: undefined, after: "x" },
    ]);
    expect(auditChanges(auditFixture({ before: { name: "x" }, after: null }))).toEqual([
      { field: "name", before: "x", after: undefined },
    ]);
  });

  it("derives filter options from the entries actually loaded", () => {
    const facets = auditFacets([
      auditFixture({ action: "user.updated", actor: "a@x.com" }),
      auditFixture({ action: "role.created", actor: "b@x.com" }),
      auditFixture({ action: "user.updated", actor: null }),
    ]);
    expect(facets.actions).toEqual(["role.created", "user.updated"]);
    expect(facets.entities).toEqual(["role", "user"]);
    expect(facets.actors).toEqual(["a@x.com", "b@x.com"]);
  });

  it("filters by action, entity, actor and free text", () => {
    const entries = [
      auditFixture({ id: 1, action: "user.updated", actor: "a@x.com" }),
      auditFixture({ id: 2, action: "role.created", actor: "b@x.com", ip_address: "9.9.9.9" }),
    ];
    const base = { q: "", action: "", entity: "", actor: "", page: 1 };
    expect(filterAudit(entries, { ...base, action: "role.created" }).map((e) => e.id)).toEqual([2]);
    expect(filterAudit(entries, { ...base, entity: "user" }).map((e) => e.id)).toEqual([1]);
    expect(filterAudit(entries, { ...base, actor: "b@x.com" }).map((e) => e.id)).toEqual([2]);
    expect(filterAudit(entries, { ...base, q: "9.9.9" }).map((e) => e.id)).toEqual([2]);
  });
});

describe("AuditDetailDialog", () => {
  it("shows the diff and the entry's identity", () => {
    withProviders(<AuditDetailDialog entry={auditFixture()} onClose={vi.fn()} />);
    expect(screen.getByText("user.updated")).toBeInTheDocument();
    expect(screen.getByText("priya@example.com")).toBeInTheDocument();
    expect(screen.getByText("10.0.0.4")).toBeInTheDocument();
    expect(screen.getByText("Priya S.")).toBeInTheDocument();
  });

  it("says so when an action recorded no field change", () => {
    withProviders(
      <AuditDetailDialog entry={auditFixture({ before: null, after: null })} onClose={vi.fn()} />,
    );
    expect(screen.getByText(/recorded no field-level change/)).toBeInTheDocument();
  });

  it("marks a security event", () => {
    withProviders(
      <AuditDetailDialog entry={auditFixture({ action: "user.login_failed" })} onClose={vi.fn()} />,
    );
    expect(screen.getByText("Security")).toBeInTheDocument();
  });
});

// --- Shared pagination ----------------------------------------------------------------------------

describe("AdminPagination", () => {
  it("pluralises a noun that does not just take an s", () => {
    withProviders(
      <AdminPagination
        page={1}
        totalPages={1}
        total={4}
        noun="entry"
        nounPlural="entries"
        filtered={false}
        onGoTo={vi.fn()}
      />,
    );
    expect(screen.getByText(/4 entries/)).toBeInTheDocument();
  });

  it("states plainly when the server returned less than it holds", () => {
    withProviders(
      <AdminPagination
        page={1}
        totalPages={1}
        total={50}
        noun="user"
        filtered={false}
        onGoTo={vi.fn()}
        truncatedTo={{ loaded: 50, available: 120 }}
      />,
    );
    expect(screen.getByText(/120 users exist/)).toBeInTheDocument();
  });

  it("says nothing about truncation when everything is loaded", () => {
    withProviders(
      <AdminPagination
        page={1}
        totalPages={1}
        total={5}
        noun="user"
        filtered={false}
        onGoTo={vi.fn()}
        truncatedTo={{ loaded: 5, available: 5 }}
      />,
    );
    expect(screen.queryByText(/exist;/)).not.toBeInTheDocument();
  });
});

// --- Navigation -----------------------------------------------------------------------------------

describe("navigation — administration entry", () => {
  it("is visible to someone holding any one administration permission", () => {
    const onlyAudit = (code: string) => code === "audit:read";
    expect(visibleNavItems(onlyAudit).map((item) => item.path)).toContain("/admin");
  });

  it("is hidden from someone holding none of them", () => {
    const noAdmin = (code: string) => code === "inbox:read";
    expect(visibleNavItems(noAdmin).map((item) => item.path)).not.toContain("/admin");
  });
});

// --- Panels (real hooks, stubbed transport) ---------------------------------------------------------

describe("UsersPanel", () => {
  function seed(users: User[], total = users.length) {
    responses["/api/v1/users"] = { data: users, page: { limit: 50, has_more: false, total } };
    responses["/api/v1/roles"] = [roleFixture()];
  }

  it("lists users with their roles and status", async () => {
    seed([userFixture({ id: "u-other", full_name: "Anita", roles: ["agent"] })]);
    withProviders(<UsersPanel />);

    expect(await screen.findByText("Anita")).toBeInTheDocument();
    // Scoped to the row: "Active" is also a status-filter option.
    const row = screen.getAllByRole("row").find((entry) => within(entry).queryByText("Anita"))!;
    expect(within(row).getByText("Active")).toBeInTheDocument();
    expect(within(row).getAllByText("agent").length).toBeGreaterThan(0);
  });

  it("offers Disable for other accounts but not for your own", async () => {
    seed([
      userFixture({ id: "u-me", full_name: "Me" }),
      userFixture({ id: "u-other", full_name: "Someone Else" }),
    ]);
    withProviders(<UsersPanel />);

    await screen.findByText("Someone Else");
    const rows = screen.getAllByRole("row");
    const mine = rows.find((row) => within(row).queryByText("Me"))!;
    const theirs = rows.find((row) => within(row).queryByText("Someone Else"))!;

    expect(within(mine).queryByRole("button", { name: "Disable" })).not.toBeInTheDocument();
    expect(within(mine).getByText("You")).toBeInTheDocument();
    expect(within(theirs).getByRole("button", { name: "Disable" })).toBeInTheDocument();
  });

  it("hides every write control from a read-only administrator", async () => {
    permissions.value = ["users:read"];
    seed([userFixture({ id: "u-other", full_name: "Anita" })]);
    withProviders(<UsersPanel />);

    await screen.findByText("Anita");
    expect(screen.queryByRole("button", { name: "New user" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
  });

  it("filters by status without a round trip", async () => {
    seed([
      userFixture({ id: "a", full_name: "Anita", is_active: true }),
      userFixture({ id: "b", full_name: "Bala", is_active: false }),
    ]);
    withProviders(<UsersPanel />);

    await screen.findByText("Anita");
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "inactive" } });

    await waitFor(() => expect(screen.queryByText("Anita")).not.toBeInTheDocument());
    expect(screen.getByText("Bala")).toBeInTheDocument();
  });

  it("says when the roster is larger than the page that was loaded", async () => {
    seed([userFixture({ id: "u-other" })], 120);
    withProviders(<UsersPanel />);
    expect(await screen.findByText(/120 users exist/)).toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<UsersPanel />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});
