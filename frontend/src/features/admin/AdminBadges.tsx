import type { ApiKeyState } from "@/features/admin/types";
import { API_KEY_STATE_LABELS } from "@/features/admin/types";

function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

export function StatusChip({ active }: { active: boolean }): JSX.Element {
  return (
    <span className={chip(active ? "border-success text-success" : "border-border text-text-disabled")}>
      {active ? "Active" : "Disabled"}
    </span>
  );
}

/** A role, marked so a seeded one reads differently from a role someone here created. */
export function RoleChip({ name, system }: { name: string; system?: boolean }): JSX.Element {
  return (
    <span className={chip(system ? "border-info text-info" : "border-border text-text-secondary")}>
      {name}
    </span>
  );
}

/**
 * Owner bypasses every permission check, so it is worth marking wherever a user is listed — a
 * superuser's effective access is not what their roles suggest.
 */
export function SuperuserChip(): JSX.Element {
  return <span className={chip("border-warning text-warning")}>Superuser</span>;
}

const KEY_TONE: Record<ApiKeyState, string> = {
  active: "border-success text-success",
  expired: "border-warning text-warning",
  revoked: "border-border text-text-disabled",
};

export function ApiKeyStateChip({ state }: { state: ApiKeyState }): JSX.Element {
  return <span className={chip(KEY_TONE[state])}>{API_KEY_STATE_LABELS[state]}</span>;
}

/** A permission code, rendered as the `resource:action` pair it is. */
export function PermissionChip({ code }: { code: string }): JSX.Element {
  return <span className={chip("border-border font-mono text-text-secondary")}>{code}</span>;
}

/** Marks a login failure or a token-reuse detection in a long audit list. */
export function SecurityChip(): JSX.Element {
  return <span className={chip("border-danger text-danger")}>Security</span>;
}
