import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type User = components["schemas"]["UserResponse"];
export type UsersPage = components["schemas"]["UsersPage"];
export type UserCreateRequest = components["schemas"]["UserCreateRequest"];
export type UserUpdateRequest = components["schemas"]["UserUpdateRequest"];

export type Role = components["schemas"]["RoleResponse"];
export type RoleCreateRequest = components["schemas"]["RoleCreateRequest"];
export type RoleUpdateRequest = components["schemas"]["RoleUpdateRequest"];
export type Permission = components["schemas"]["PermissionResponse"];

export type ApiKey = components["schemas"]["ApiKeyResponse"];
export type ApiKeyCreated = components["schemas"]["ApiKeyCreateResponse"];
export type ApiKeyCreateRequest = components["schemas"]["ApiKeyCreateRequest"];

export type AuditEntry = components["schemas"]["AuditLogResponse"];
export type AuditPage = components["schemas"]["AuditLogPage"];

/**
 * The preset system roles the platform seeds (Doc 01 §2.4).
 *
 * `RoleResponse.is_system` is the authority on whether a role may be deleted — this list only
 * supplies the plain-language description of what each shipped role is *for*, which the role's own
 * `description` does not always carry. A role not listed here (a custom one) simply shows its own
 * description.
 */
export const SYSTEM_ROLE_SUMMARIES: Record<string, string> = {
  owner: "Full control of the platform, including security and destructive operations.",
  admin: "Runs the platform day to day. Everything except owner-only actions.",
  manager: "Contacts, segments, templates, campaigns and analytics.",
  agent: "Front-line support: the inbox, messaging and their own follow-up tasks.",
  analyst: "Read-only insight — analytics and reports, with no ability to send.",
};

// --- Users --------------------------------------------------------------------------------------

export type UserSort = "name" | "-name" | "-created_at" | "created_at" | "-last_login_at";

export interface UserListQuery {
  q: string;
  /** "" = any · "active" · "inactive" */
  status: string;
  role: string;
  sort: UserSort;
  page: number;
}

export const DEFAULT_USER_QUERY: UserListQuery = {
  q: "",
  status: "",
  role: "",
  sort: "name",
  page: 1,
};

export const USER_STATUS_LABELS: Record<string, string> = {
  active: "Active",
  inactive: "Disabled",
};

/** A user is disabled by deactivating them, which also revokes their sessions. */
export function isDisabled(user: User): boolean {
  return !user.is_active;
}

// --- API keys -----------------------------------------------------------------------------------

export type ApiKeyState = "active" | "expired" | "revoked";

export const API_KEY_STATE_LABELS: Record<ApiKeyState, string> = {
  active: "Active",
  expired: "Expired",
  revoked: "Revoked",
};

/**
 * A key's effective state.
 *
 * `is_active` is the stored flag, but an unexpired-but-past-`expires_at` key is no longer usable
 * either — reporting it as "Active" because nothing has revoked it would misstate the one thing
 * this column exists to answer.
 */
export function apiKeyState(key: ApiKey, now: number = Date.now()): ApiKeyState {
  if (key.revoked_at || !key.is_active) return "revoked";
  if (key.expires_at && Date.parse(key.expires_at) <= now) return "expired";
  return "active";
}

// --- Audit --------------------------------------------------------------------------------------

export interface AuditListQuery {
  q: string;
  action: string;
  entity: string;
  actor: string;
  page: number;
}

export const DEFAULT_AUDIT_QUERY: AuditListQuery = {
  q: "",
  action: "",
  entity: "",
  actor: "",
  page: 1,
};

/**
 * Audit actions are dotted `entity.verb` strings from a large, growing vocabulary
 * (`AuditAction`), and the contract types the field as `str`. Rather than restate ~80 constants
 * that would drift, the filter options are derived from the entries actually loaded, and this
 * turns a code into a readable phrase.
 */
export function humanizeAction(action: string): string {
  const [, verb = ""] = action.split(".");
  const words = verb.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

export function actionEntity(action: string): string {
  const [entity = ""] = action.split(".");
  return entity;
}

/** Actions that record a security-relevant failure, worth marking in a long list. */
export function isSecurityEvent(action: string): boolean {
  return (
    action === "user.login_failed" ||
    action === "user.login_locked" ||
    action === "user.token_reuse_detected"
  );
}
