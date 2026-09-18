import type { ApiKeyState, AuditIntegrity } from "@/features/admin/types";
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

const INTEGRITY: Record<AuditIntegrity, { label: string; tone: string; title: string }> = {
  verified: {
    label: "Verified",
    tone: "border-success text-success",
    title: "This entry still reproduces the digest stored when it was written.",
  },
  verified_legacy: {
    label: "Content verified",
    tone: "border-info text-info",
    title:
      "Written before the digest covered the timestamp. The recorded content is intact; the time it carries is not vouched for.",
  },
  mismatch: {
    label: "Does not match",
    tone: "border-danger text-danger",
    title: "This entry no longer reproduces its digest — its content changed after it was written.",
  },
  unhashed: {
    label: "No digest",
    tone: "border-border text-text-disabled",
    title: "No digest was stored for this entry, so there is nothing to check it against.",
  },
};

/**
 * Whether an audit entry still vouches for itself.
 *
 * Shown rather than kept server-side because the person reading the trail is the person who needs
 * to know whether to trust it, and the four verdicts say different things: a mismatch is an alarm,
 * while a pre-fix row is intact content with an unprotected timestamp, not a finding.
 */
export function IntegrityChip({ integrity }: { integrity: AuditIntegrity }): JSX.Element {
  const { label, tone, title } = INTEGRITY[integrity];
  return (
    <span className={chip(tone)} title={title}>
      {label}
    </span>
  );
}
