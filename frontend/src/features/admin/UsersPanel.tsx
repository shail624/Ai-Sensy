import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import { AdminPagination } from "@/features/admin/AdminPagination";
import { RoleChip, StatusChip, SuperuserChip } from "@/features/admin/AdminBadges";
import {
  apiErrorMessage,
  useHasPermission,
  useRoles,
  useSetUserActive,
  useUsers,
} from "@/features/admin/api";
import { canToggleActive, selectUserPage, userSummary } from "@/features/admin/selectors";
import { UserFormDialog } from "@/features/admin/UserFormDialog";
import type { User, UserListQuery, UserSort } from "@/features/admin/types";
import { DEFAULT_USER_QUERY } from "@/features/admin/types";
import { useAuth } from "@/lib/auth";
import { formatCount, formatDateTime, UNKNOWN } from "@/lib/format";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

const SORTS: UserSort[] = ["name", "-name", "-created_at", "created_at", "-last_login_at"];

const SORT_LABELS: Record<UserSort, string> = {
  name: "Name (A–Z)",
  "-name": "Name (Z–A)",
  "-created_at": "Newest",
  created_at: "Oldest",
  "-last_login_at": "Recently signed in",
};

function readQuery(params: URLSearchParams): UserListQuery {
  const status = params.get("status") ?? "";
  const sort = params.get("sort") ?? "";
  const page = Number.parseInt(params.get("page") ?? "", 10);
  return {
    q: params.get("q") ?? "",
    status: status === "active" || status === "inactive" ? status : "",
    role: params.get("role") ?? "",
    sort: SORTS.includes(sort as UserSort) ? (sort as UserSort) : DEFAULT_USER_QUERY.sort,
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

function writeQuery(query: UserListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.status) params.set("status", query.status);
  if (query.role) params.set("role", query.role);
  if (query.sort !== DEFAULT_USER_QUERY.sort) params.set("sort", query.sort);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

/**
 * User administration (Doc 05 B11.1) — list, search, filter, create, edit and disable.
 *
 * Disabling is the real containment action: it revokes the account's sessions as well as blocking
 * sign-in. It is never offered on the signed-in administrator's own row, because locking yourself
 * out is the one mistake this screen could make that cannot be undone from the browser.
 */
export function UsersPanel(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [editing, setEditing] = useState<User | null>(null);
  const [creating, setCreating] = useState(false);
  const [disabling, setDisabling] = useState<User | null>(null);

  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canManage = useHasPermission("users:manage");
  const { user: me } = useAuth();

  const users = useUsers();
  const roles = useRoles();
  const setActive = useSetUserActive();

  const rows = useMemo(() => users.data?.data ?? [], [users.data]);
  const page = useMemo(() => selectUserPage(rows, query), [rows, query]);
  const summary = useMemo(() => userSummary(rows), [rows]);
  const loadedTotal = users.data?.page.total ?? rows.length;

  const isFiltered = query.q !== "" || query.status !== "" || query.role !== "";

  function apply(next: Partial<UserListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next, page: 1 }));
  }

  if (users.isLoading) return <Spinner label="Loading users…" />;

  if (users.isError) {
    return <ErrorState message={apiErrorMessage(users.error)} onRetry={() => void users.refetch()} />;
  }

  return (
    <>
      <p className="mb-3 text-sm text-text-secondary">
        {formatCount(summary.total)} user{summary.total === 1 ? "" : "s"} ·{" "}
        {formatCount(summary.active)} active · {formatCount(summary.disabled)} disabled
        {summary.neverSignedIn > 0
          ? ` · ${formatCount(summary.neverSignedIn)} never signed in`
          : ""}
      </p>

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
            <label htmlFor="users-search" className="text-xs font-medium text-text-secondary">
              Search
            </label>
            <input
              id="users-search"
              type="search"
              value={query.q}
              onChange={(event) => apply({ q: event.target.value })}
              placeholder="Name or email…"
              className={FIELD_CLASS}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="users-status" className="text-xs font-medium text-text-secondary">
              Status
            </label>
            <select
              id="users-status"
              value={query.status}
              onChange={(event) => apply({ status: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="inactive">Disabled</option>
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="users-role" className="text-xs font-medium text-text-secondary">
              Role
            </label>
            <select
              id="users-role"
              value={query.role}
              onChange={(event) => apply({ role: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">All roles</option>
              {(roles.data ?? []).map((role) => (
                <option key={role.id} value={role.name}>
                  {role.name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="users-sort" className="text-xs font-medium text-text-secondary">
              Sort
            </label>
            <select
              id="users-sort"
              value={query.sort}
              onChange={(event) => apply({ sort: event.target.value as UserSort })}
              className={FIELD_CLASS}
            >
              {SORTS.map((sort) => (
                <option key={sort} value={sort}>
                  {SORT_LABELS[sort]}
                </option>
              ))}
            </select>
          </div>
        </div>

        {canManage ? (
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            New user
          </button>
        ) : null}
      </div>

      {setActive.error ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(setActive.error)} />
        </div>
      ) : null}

      {rows.length === 0 ? (
        <EmptyState title="No users" description="This organization has no user accounts yet." />
      ) : page.rows.length === 0 ? (
        <EmptyState title="No users match these filters" description="Try a different name, status or role." />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">User</th>
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Roles</th>
                  <th scope="col" className="px-3 py-2">Status</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Last signed in</th>
                  <th scope="col" className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {page.rows.map((user) => (
                  <tr key={user.id} className="border-b border-border last:border-0 hover:bg-hover">
                    <td className="px-3 py-2">
                      <p className="font-medium text-text-primary">{user.full_name}</p>
                      <p className="truncate text-xs text-text-secondary">{user.email}</p>
                      <div className="mt-1 flex flex-wrap gap-1 md:hidden">
                        {user.roles.map((role) => (
                          <RoleChip key={role} name={role} />
                        ))}
                      </div>
                    </td>
                    <td className="hidden px-3 py-2 md:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {user.roles.length === 0 ? (
                          <span className="text-xs text-text-disabled">No role</span>
                        ) : (
                          user.roles.map((role) => <RoleChip key={role} name={role} />)
                        )}
                        {user.is_superuser ? <SuperuserChip /> : null}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <StatusChip active={user.is_active} />
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                      {user.last_login_at ? formatDateTime(user.last_login_at) : UNKNOWN}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap justify-end gap-1">
                        {canManage ? (
                          <button
                            type="button"
                            className={ACTION_CLASS}
                            onClick={() => setEditing(user)}
                          >
                            Edit
                          </button>
                        ) : null}
                        {canManage && canToggleActive(user, me?.id) ? (
                          user.is_active ? (
                            <button
                              type="button"
                              className={`${ACTION_CLASS} text-danger`}
                              onClick={() => setDisabling(user)}
                            >
                              Disable
                            </button>
                          ) : (
                            <button
                              type="button"
                              className={ACTION_CLASS}
                              disabled={setActive.isPending}
                              onClick={() =>
                                setActive.mutate({ userId: user.id, active: true })
                              }
                            >
                              Enable
                            </button>
                          )
                        ) : null}
                        {canManage && !canToggleActive(user, me?.id) ? (
                          <span className="text-xs text-text-disabled">You</span>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <AdminPagination
            page={page.page}
            totalPages={page.totalPages}
            total={page.total}
            noun="user"
            filtered={isFiltered}
            onGoTo={(next) => setSearchParams(writeQuery({ ...query, page: next }))}
            truncatedTo={{ loaded: rows.length, available: loadedTotal }}
          />
        </>
      )}

      {creating ? <UserFormDialog onClose={() => setCreating(false)} /> : null}
      {editing ? <UserFormDialog user={editing} onClose={() => setEditing(null)} /> : null}

      {disabling ? (
        <ConfirmDialog
          title={`Disable ${disabling.full_name}?`}
          body="They are signed out immediately and cannot sign in again until the account is re-enabled. Nothing they created is removed."
          confirmLabel="Disable account"
          destructive
          pending={setActive.isPending}
          error={setActive.error}
          onClose={() => setDisabling(null)}
          onConfirm={() =>
            setActive.mutate(
              { userId: disabling.id, active: false },
              { onSuccess: () => setDisabling(null) },
            )
          }
        />
      ) : null}
    </>
  );
}
