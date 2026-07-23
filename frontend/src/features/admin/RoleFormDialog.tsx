import { useState } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useCreateRole, useUpdateRole } from "@/features/admin/api";
import type { Role } from "@/features/admin/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

interface Props {
  /** Present → rename that role; absent → create a custom one. */
  role?: Role;
  onClose: () => void;
  onCreated?: (role: Role) => void;
}

/**
 * Create or rename a role (Doc 05 B11.2).
 *
 * Only the name and description are set here — a role's permission set is replaced as a whole by
 * its own endpoint, and doing both in one dialog would make a partial failure ambiguous. A new role
 * starts with no permissions, so the caller is handed straight to the matrix to grant them.
 */
export function RoleFormDialog({ role, onClose, onCreated }: Props): JSX.Element {
  const editing = role !== undefined;
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [showErrors, setShowErrors] = useState(false);

  const create = useCreateRole();
  const update = useUpdateRole();
  const pending = create.isPending || update.isPending;
  const error = create.error ?? update.error;

  const problem =
    name.trim() === ""
      ? "Name is required"
      : name.trim().length > 80
        ? "Name is too long"
        : null;

  function submit(): void {
    setShowErrors(true);
    if (problem) return;

    const body = { name: name.trim(), description: description.trim() || null };
    if (editing) {
      update.mutate({ roleId: role.id, body }, { onSuccess: onClose });
      return;
    }
    create.mutate(
      { ...body, permissions: [] },
      {
        onSuccess: (created) => {
          onCreated?.(created);
          onClose();
        },
      },
    );
  }

  return (
    <Modal title={editing ? `Rename "${role.name}"` : "New role"} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label htmlFor="role-name" className={LABEL_CLASS}>
            Name
          </label>
          <input
            id="role-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="regional_supervisor"
            className={FIELD_CLASS}
          />
          {showErrors && problem ? <p className="text-xs text-danger">{problem}</p> : null}
        </div>

        <div>
          <label htmlFor="role-description" className={LABEL_CLASS}>
            Description
          </label>
          <textarea
            id="role-description"
            rows={2}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="What this role is for, in one line."
            className={FIELD_CLASS}
          />
        </div>

        {!editing ? (
          <p className="text-xs text-text-disabled">
            A new role starts with no permissions. You will be taken to the matrix to grant them.
          </p>
        ) : null}

        {error ? <p className="text-sm text-danger">{apiErrorMessage(error)}</p> : null}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={pending}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={pending}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            {pending ? "Saving…" : editing ? "Save changes" : "Create role"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
