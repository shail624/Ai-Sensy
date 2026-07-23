import { useMemo, useState } from "react";

import { Modal, Spinner } from "@/components/ui";
import { apiErrorMessage, useUpdateUser, useUsers } from "@/features/admin/api";
import { matchesUser } from "@/features/admin/selectors";
import type { Role, User } from "@/features/admin/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

interface Props {
  role: Role;
  onClose: () => void;
}

/**
 * Assign or unassign users to a role (Doc 05 B11.2).
 *
 * There is no `roles/{id}/users` endpoint, and there does not need to be: role membership lives on
 * the user, so this composes from the endpoint that owns it — one `PATCH /users/{id}` per changed
 * account, each carrying that user's full role list plus or minus this one.
 *
 * Only the changed users are written. Sending every user on the screen would produce audit entries
 * for accounts nobody touched, and the audit trail is the thing this whole area exists to keep
 * trustworthy.
 */
export function RoleAssignDialog({ role, onClose }: Props): JSX.Element {
  const users = useUsers();
  const update = useUpdateUser();

  const all = useMemo(() => users.data?.data ?? [], [users.data]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(
    () => new Set(all.filter((user) => user.roles.includes(role.name)).map((user) => user.id)),
  );
  const [failed, setFailed] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);

  const shown = all.filter((user) => matchesUser(user, search));
  const originally = useMemo(
    () => new Set(all.filter((user) => user.roles.includes(role.name)).map((user) => user.id)),
    [all, role.name],
  );

  const changed = all.filter((user) => selected.has(user.id) !== originally.has(user.id));

  function toggle(id: string): void {
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function rolesFor(user: User): string[] {
    const keep = user.roles.filter((name) => name !== role.name);
    return selected.has(user.id) ? [...keep, role.name] : keep;
  }

  async function save(): Promise<void> {
    setSaving(true);
    setFailed([]);
    const problems: string[] = [];

    // Sequential rather than parallel: each write carries the user's own `row_version`, and a burst
    // of concurrent updates against the same list is how version conflicts get manufactured.
    for (const user of changed) {
      try {
        await update.mutateAsync({
          userId: user.id,
          body: { roles: rolesFor(user), row_version: user.row_version },
        });
      } catch (error) {
        problems.push(`${user.full_name}: ${apiErrorMessage(error)}`);
      }
    }

    setSaving(false);
    if (problems.length > 0) {
      setFailed(problems);
      return;
    }
    onClose();
  }

  return (
    <Modal title={`Who has "${role.name}"`} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label htmlFor="assign-search" className="text-xs font-medium text-text-secondary">
            Search
          </label>
          <input
            id="assign-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Name or email…"
            className={FIELD_CLASS}
          />
        </div>

        {users.isLoading ? (
          <Spinner label="Loading users…" />
        ) : (
          <div className="max-h-72 overflow-y-auto rounded-md border border-border">
            {shown.length === 0 ? (
              <p className="p-3 text-sm text-text-disabled">No users match.</p>
            ) : (
              <ul>
                {shown.map((user) => (
                  <li key={user.id} className="border-b border-border last:border-0">
                    <label className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-hover">
                      <input
                        type="checkbox"
                        checked={selected.has(user.id)}
                        onChange={() => toggle(user.id)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-text-primary">{user.full_name}</span>
                        <span className="block truncate text-xs text-text-secondary">
                          {user.email}
                        </span>
                      </span>
                      {!user.is_active ? (
                        <span className="text-xs text-text-disabled">disabled</span>
                      ) : null}
                    </label>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <p className="text-xs text-text-disabled">
          {changed.length === 0
            ? "No changes yet."
            : `${changed.length} account${changed.length === 1 ? "" : "s"} will be updated.`}
        </p>

        {failed.length > 0 ? (
          <ul role="alert" className="space-y-1">
            {failed.map((message) => (
              <li key={message} className="text-xs text-danger">
                {message}
              </li>
            ))}
          </ul>
        ) : null}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={saving}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={() => void save()}
            disabled={saving || changed.length === 0}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            {saving ? "Saving…" : "Save assignments"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
