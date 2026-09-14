import { useState } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useCreateUser, useRoles, useUpdateUser } from "@/features/admin/api";
import type { User } from "@/features/admin/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

/** Minimum the server's own policy accepts; it re-checks and its 422 is what decides. */
const MIN_PASSWORD = 12;

interface Props {
  /** Present → edit that user; absent → create a new one. */
  user?: User;
  onClose: () => void;
}

interface Draft {
  email: string;
  full_name: string;
  password: string;
  phone: string;
  timezone: string;
  locale: string;
  roles: string[];
}

function draftFor(user: User | undefined): Draft {
  return {
    email: user?.email ?? "",
    full_name: user?.full_name ?? "",
    password: "",
    phone: user?.phone ?? "",
    timezone: user?.timezone ?? "UTC",
    locale: user?.locale ?? "en",
    roles: user?.roles ?? [],
  };
}

/**
 * Create or edit a user (Doc 05 B11.1).
 *
 * Email is set once: the contract's update model does not accept it, because it is the identity
 * the account signs in with. Roles are chosen from the live catalog, and an edit carries
 * `row_version` so a concurrent change surfaces as the server's conflict rather than silently
 * overwriting.
 */
export function UserFormDialog({ user, onClose }: Props): JSX.Element {
  const editing = user !== undefined;
  const [draft, setDraft] = useState<Draft>(() => draftFor(user));
  const [showErrors, setShowErrors] = useState(false);

  const roles = useRoles();
  const create = useCreateUser();
  const update = useUpdateUser();

  const pending = create.isPending || update.isPending;
  const error = create.error ?? update.error;

  const problems: Partial<Record<keyof Draft, string>> = {};
  if (draft.full_name.trim() === "") problems.full_name = "Name is required";
  if (!editing) {
    if (!/^\S+@\S+\.\S+$/.test(draft.email.trim())) problems.email = "Enter a valid email address";
    if (draft.password.length < MIN_PASSWORD) {
      problems.password = `Use at least ${MIN_PASSWORD} characters`;
    }
  }
  const visible = showErrors ? problems : {};

  function set<K extends keyof Draft>(key: K, value: Draft[K]): void {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function toggleRole(name: string): void {
    set(
      "roles",
      draft.roles.includes(name)
        ? draft.roles.filter((role) => role !== name)
        : [...draft.roles, name],
    );
  }

  function submit(): void {
    setShowErrors(true);
    if (Object.keys(problems).length > 0) return;

    if (editing) {
      update.mutate(
        {
          userId: user.id,
          body: {
            full_name: draft.full_name.trim(),
            phone: draft.phone.trim() || null,
            timezone: draft.timezone.trim(),
            locale: draft.locale.trim(),
            roles: draft.roles,
            row_version: user.row_version,
          },
        },
        { onSuccess: onClose },
      );
      return;
    }
    create.mutate(
      {
        email: draft.email.trim(),
        full_name: draft.full_name.trim(),
        password: draft.password,
        phone: draft.phone.trim() || null,
        timezone: draft.timezone.trim(),
        locale: draft.locale.trim(),
        roles: draft.roles,
      },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal title={editing ? `Edit ${user.full_name}` : "New user"} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label htmlFor="user-email" className={LABEL_CLASS}>
            Email
          </label>
          <input
            id="user-email"
            type="email"
            value={draft.email}
            disabled={editing}
            onChange={(event) => set("email", event.target.value)}
            className={`${FIELD_CLASS} disabled:opacity-60`}
          />
          {editing ? (
            <p className="mt-1 text-xs text-text-disabled">
              The sign-in address cannot be changed here.
            </p>
          ) : null}
          {visible.email ? <p className="text-xs text-danger">{visible.email}</p> : null}
        </div>

        <div>
          <label htmlFor="user-name" className={LABEL_CLASS}>
            Full name
          </label>
          <input
            id="user-name"
            value={draft.full_name}
            onChange={(event) => set("full_name", event.target.value)}
            className={FIELD_CLASS}
          />
          {visible.full_name ? <p className="text-xs text-danger">{visible.full_name}</p> : null}
        </div>

        {!editing ? (
          <div>
            <label htmlFor="user-password" className={LABEL_CLASS}>
              Initial password
            </label>
            <input
              id="user-password"
              type="password"
              value={draft.password}
              onChange={(event) => set("password", event.target.value)}
              className={FIELD_CLASS}
            />
            <p className="mt-1 text-xs text-text-disabled">
              Share it over a channel the person already trusts. They can change it from their own
              profile; there is no administrator-initiated reset.
            </p>
            {visible.password ? <p className="text-xs text-danger">{visible.password}</p> : null}
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div>
            <label htmlFor="user-phone" className={LABEL_CLASS}>
              Phone
            </label>
            <input
              id="user-phone"
              value={draft.phone}
              onChange={(event) => set("phone", event.target.value)}
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label htmlFor="user-timezone" className={LABEL_CLASS}>
              Timezone
            </label>
            <input
              id="user-timezone"
              value={draft.timezone}
              onChange={(event) => set("timezone", event.target.value)}
              placeholder="Asia/Kolkata"
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label htmlFor="user-locale" className={LABEL_CLASS}>
              Locale
            </label>
            <input
              id="user-locale"
              value={draft.locale}
              onChange={(event) => set("locale", event.target.value)}
              className={FIELD_CLASS}
            />
          </div>
        </div>

        <fieldset>
          <legend className={LABEL_CLASS}>Roles</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {(roles.data ?? []).map((role) => {
              const selected = draft.roles.includes(role.name);
              return (
                <button
                  key={role.id}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => toggleRole(role.name)}
                  className={`rounded-full border px-3 py-1 text-xs ${
                    selected
                      ? "border-accent text-accent"
                      : "border-border text-text-secondary hover:bg-hover"
                  }`}
                >
                  {role.name}
                </button>
              );
            })}
          </div>
          {draft.roles.length === 0 ? (
            <p className="mt-2 text-xs text-warning">
              With no role, this account can sign in but do nothing.
            </p>
          ) : null}
        </fieldset>

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
            {pending ? "Saving…" : editing ? "Save changes" : "Create user"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
