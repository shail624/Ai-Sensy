import { EmptyState } from "@/components/ui";
import { groupPermissions } from "@/features/admin/selectors";
import type { Permission, Role } from "@/features/admin/types";

interface Props {
  permissions: Permission[];
  roles: Role[];
  /** When set, that role's row is editable and every toggle calls back. */
  editingRoleId?: string;
  draft?: string[];
  onToggle?: (code: string) => void;
  onToggleResource?: (codes: string[], grant: boolean) => void;
}

/**
 * Every permission in the catalog against every role (Doc 05 B11.2/B11.3).
 *
 * Grouped by resource in catalog order, because the matrix is only readable if `contacts:*` sit
 * together — the seed order already reflects how the permissions were designed.
 *
 * A **system role is shown but never editable**: the shipped roles are the baseline the platform
 * documents, and editing one in place would silently change what "agent" means for everyone. To
 * diverge, create a custom role. The server enforces the same rule.
 *
 * The Owner user additionally holds superuser and bypasses every check, so its column reflects the
 * role's grants, not that user's effective access — noted below the table rather than implied.
 */
export function PermissionMatrix({
  permissions,
  roles,
  editingRoleId,
  draft,
  onToggle,
  onToggleResource,
}: Props): JSX.Element {
  const groups = groupPermissions(permissions);

  if (permissions.length === 0) {
    return <EmptyState title="No permissions" description="The catalog has not been seeded." />;
  }

  function holds(role: Role, code: string): boolean {
    if (editingRoleId && role.id === editingRoleId && draft) return draft.includes(code);
    return role.permissions.includes(code);
  }

  return (
    <div>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
            <tr>
              <th scope="col" className="sticky left-0 z-10 bg-surface-2 px-3 py-2">
                Permission
              </th>
              {roles.map((role) => (
                <th key={role.id} scope="col" className="px-3 py-2 text-center">
                  <span className={role.id === editingRoleId ? "text-accent" : undefined}>
                    {role.name}
                  </span>
                  {role.is_system ? (
                    <span className="block text-[10px] font-normal text-text-disabled">system</span>
                  ) : null}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => {
              const codes = group.permissions.map((permission) => permission.code);
              const editingRole = roles.find((role) => role.id === editingRoleId);
              const allGranted =
                editingRole !== undefined && codes.every((code) => holds(editingRole, code));

              return [
                <tr key={`${group.resource}-header`} className="bg-surface-2/60">
                  <th
                    scope="rowgroup"
                    colSpan={roles.length + 1}
                    className="px-3 py-1.5 text-left text-xs font-semibold uppercase tracking-wide text-text-secondary"
                  >
                    {group.resource}
                    {editingRoleId && onToggleResource ? (
                      <button
                        type="button"
                        onClick={() => onToggleResource(codes, !allGranted)}
                        className="ml-2 rounded border border-border px-1.5 py-0.5 text-[10px] font-normal normal-case text-text-secondary hover:bg-hover"
                      >
                        {allGranted ? "Clear all" : "Grant all"}
                      </button>
                    ) : null}
                  </th>
                </tr>,
                ...group.permissions.map((permission) => (
                  <tr
                    key={permission.code}
                    className="border-b border-border last:border-0 hover:bg-hover"
                  >
                    <td className="sticky left-0 z-10 bg-surface px-3 py-2">
                      <p className="font-mono text-xs text-text-primary">{permission.code}</p>
                      {permission.description ? (
                        <p className="text-xs text-text-secondary">{permission.description}</p>
                      ) : null}
                    </td>
                    {roles.map((role) => {
                      const granted = holds(role, permission.code);
                      const editable = role.id === editingRoleId && !role.is_system;
                      return (
                        <td key={role.id} className="px-3 py-2 text-center">
                          {editable && onToggle ? (
                            <input
                              type="checkbox"
                              checked={granted}
                              aria-label={`${permission.code} for ${role.name}`}
                              onChange={() => onToggle(permission.code)}
                            />
                          ) : (
                            <span
                              aria-label={
                                granted
                                  ? `${role.name} has ${permission.code}`
                                  : `${role.name} does not have ${permission.code}`
                              }
                              className={granted ? "text-success" : "text-text-disabled"}
                            >
                              {granted ? "✓" : "·"}
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                )),
              ];
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-2 text-xs text-text-disabled">
        System roles ship with the platform and cannot be edited — create a custom role to diverge.
        A user marked superuser bypasses every check regardless of the roles they hold.
      </p>
    </div>
  );
}
