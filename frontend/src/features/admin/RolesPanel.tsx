import { useMemo, useState } from "react";

import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import { RoleChip } from "@/features/admin/AdminBadges";
import {
  apiErrorMessage,
  useDeleteRole,
  useHasPermission,
  usePermissions,
  useRoles,
  useSetRolePermissions,
  useUsers,
} from "@/features/admin/api";
import { isRoleDeletable, roleUsage, sortRoles } from "@/features/admin/selectors";
import { PermissionMatrix } from "@/features/admin/PermissionMatrix";
import { RoleAssignDialog } from "@/features/admin/RoleAssignDialog";
import { RoleFormDialog } from "@/features/admin/RoleFormDialog";
import type { Role } from "@/features/admin/types";
import { SYSTEM_ROLE_SUMMARIES } from "@/features/admin/types";
import { formatCount } from "@/lib/format";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

/**
 * Role and permission administration (Doc 05 B11.2/B11.3).
 *
 * The roles list and the permission matrix are one screen because they are one decision: what a
 * role *is* is the set of permissions it holds. Editing puts a single role's column into an
 * unsaved draft, which is then written with one `PUT` of the whole set — the contract replaces
 * rather than patches, so two admins editing at once cannot merge into a set neither chose.
 */
export function RolesPanel(): JSX.Element {
  const [creating, setCreating] = useState(false);
  const [renaming, setRenaming] = useState<Role | null>(null);
  const [assigning, setAssigning] = useState<Role | null>(null);
  const [deleting, setDeleting] = useState<Role | null>(null);
  const [editingRoleId, setEditingRoleId] = useState<string | null>(null);
  const [draft, setDraft] = useState<string[]>([]);

  const canWrite = useHasPermission("roles:write");
  const roles = useRoles();
  const permissions = usePermissions();
  const users = useUsers();
  const savePermissions = useSetRolePermissions();
  const removeRole = useDeleteRole();

  const sorted = useMemo(() => sortRoles(roles.data ?? []), [roles.data]);
  const usage = useMemo(() => roleUsage(users.data?.data ?? []), [users.data]);

  const editingRole = sorted.find((role) => role.id === editingRoleId) ?? null;
  const dirty =
    editingRole !== null &&
    JSON.stringify([...draft].sort()) !== JSON.stringify([...editingRole.permissions].sort());

  function startEditing(role: Role): void {
    setEditingRoleId(role.id);
    setDraft([...role.permissions]);
  }

  function stopEditing(): void {
    setEditingRoleId(null);
    setDraft([]);
  }

  function toggle(code: string): void {
    setDraft((current) =>
      current.includes(code) ? current.filter((entry) => entry !== code) : [...current, code],
    );
  }

  function toggleResource(codes: string[], grant: boolean): void {
    setDraft((current) =>
      grant
        ? [...new Set([...current, ...codes])]
        : current.filter((entry) => !codes.includes(entry)),
    );
  }

  if (roles.isLoading || permissions.isLoading) return <Spinner label="Loading roles…" />;

  if (roles.isError || permissions.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(roles.error ?? permissions.error)}
        onRetry={() => {
          void roles.refetch();
          void permissions.refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-4">
      <Section
        title="Roles"
        action={
          canWrite ? (
            <button
              type="button"
              onClick={() => setCreating(true)}
              className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
            >
              New role
            </button>
          ) : null
        }
      >
        {sorted.length === 0 ? (
          <EmptyState title="No roles" description="The role catalog has not been seeded." />
        ) : (
          <ul className="space-y-2">
            {sorted.map((role) => {
              const holders = usage[role.name] ?? 0;
              const deletable = isRoleDeletable(role, usage);
              return (
                <li
                  key={role.id}
                  className="flex flex-wrap items-start justify-between gap-3 rounded-md border border-border p-3"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <RoleChip name={role.name} system={role.is_system} />
                      <span className="text-xs text-text-secondary">
                        {formatCount(role.permissions.length)} permissions ·{" "}
                        {formatCount(holders)} user{holders === 1 ? "" : "s"}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-text-secondary">
                      {role.description ?? SYSTEM_ROLE_SUMMARIES[role.name] ?? "No description."}
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-1">
                    {canWrite && !role.is_system ? (
                      <button
                        type="button"
                        className={ACTION_CLASS}
                        onClick={() =>
                          editingRoleId === role.id ? stopEditing() : startEditing(role)
                        }
                      >
                        {editingRoleId === role.id ? "Stop editing" : "Edit permissions"}
                      </button>
                    ) : null}
                    {canWrite && !role.is_system ? (
                      <button
                        type="button"
                        className={ACTION_CLASS}
                        onClick={() => setRenaming(role)}
                      >
                        Rename
                      </button>
                    ) : null}
                    {canWrite ? (
                      <button
                        type="button"
                        className={ACTION_CLASS}
                        onClick={() => setAssigning(role)}
                      >
                        Assign users
                      </button>
                    ) : null}
                    {canWrite && deletable ? (
                      <button
                        type="button"
                        className={`${ACTION_CLASS} text-danger`}
                        onClick={() => setDeleting(role)}
                      >
                        Delete
                      </button>
                    ) : null}
                    {canWrite && role.is_system ? (
                      <span className="self-center text-xs text-text-disabled">
                        Shipped with the platform
                      </span>
                    ) : canWrite && holders > 0 ? (
                      <span className="self-center text-xs text-text-disabled">
                        In use — cannot be deleted
                      </span>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Section>

      <Section
        title="Permission matrix"
        action={
          editingRole ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary">
                Editing <span className="text-accent">{editingRole.name}</span>
              </span>
              <button type="button" onClick={stopEditing} className={ACTION_CLASS}>
                Cancel
              </button>
              <button
                type="button"
                disabled={!dirty || savePermissions.isPending}
                onClick={() =>
                  savePermissions.mutate(
                    { roleId: editingRole.id, permissions: draft },
                    { onSuccess: stopEditing },
                  )
                }
                className="rounded-md bg-accent px-2 py-1 text-xs text-accent-fg disabled:opacity-50"
              >
                {savePermissions.isPending ? "Saving…" : "Save permissions"}
              </button>
            </div>
          ) : null
        }
      >
        {savePermissions.error ? (
          <div className="mb-3">
            <ErrorState message={apiErrorMessage(savePermissions.error)} />
          </div>
        ) : null}

        <PermissionMatrix
          permissions={permissions.data ?? []}
          roles={sorted}
          editingRoleId={editingRole?.id}
          draft={draft}
          onToggle={toggle}
          onToggleResource={toggleResource}
        />
      </Section>

      {creating ? (
        <RoleFormDialog onClose={() => setCreating(false)} onCreated={startEditing} />
      ) : null}
      {renaming ? <RoleFormDialog role={renaming} onClose={() => setRenaming(null)} /> : null}
      {assigning ? (
        <RoleAssignDialog role={assigning} onClose={() => setAssigning(null)} />
      ) : null}

      {deleting ? (
        <ConfirmDialog
          title={`Delete the "${deleting.name}" role?`}
          body="No user holds this role, so nobody loses access. The role and its permission set are removed."
          confirmLabel="Delete role"
          destructive
          pending={removeRole.isPending}
          error={removeRole.error}
          onClose={() => setDeleting(null)}
          onConfirm={() =>
            removeRole.mutate(deleting.id, {
              onSuccess: () => {
                if (editingRoleId === deleting.id) stopEditing();
                setDeleting(null);
              },
            })
          }
        />
      ) : null}
    </div>
  );
}
