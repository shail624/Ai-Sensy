import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Organization = components["schemas"]["OrganizationResponse"];
export type OrganizationUpdateRequest = components["schemas"]["OrganizationUpdateRequest"];
export type Setting = components["schemas"]["SettingResponse"];
export type SettingsUpdateRequest = components["schemas"]["SettingsUpdateRequest"];
export type FeatureFlag = components["schemas"]["FeatureFlagResponse"];
export type FeatureFlagPatchRequest = components["schemas"]["FeatureFlagPatchRequest"];
export type Preferences = components["schemas"]["PreferencesResponse"];

/**
 * Setting scope — the three values `models/settings.py` defines.
 *
 * The contract types the field as `str`, so this is the **display vocabulary**, not an API type.
 *
 * The distinction is load-bearing rather than cosmetic: `PUT /settings` upserts into the
 * **organization** scope unconditionally, so a system-scoped row cannot be edited through it.
 * Writing a system key would not change that row — it would create a second, organization-scoped
 * row with the same key, and both would then come back from the read. That is why system settings
 * are rendered read-only rather than merely discouraged.
 */
export const SCOPE_SYSTEM = "system";
export const SCOPE_ORGANIZATION = "organization";

export const SCOPE_LABELS: Record<string, string> = {
  system: "System",
  organization: "Organization",
  user: "User",
};

export const SCOPE_EXPLANATIONS: Record<string, string> = {
  system: "Set on the server and read-only here — deployment configuration, not an app setting.",
  organization: "Applies to this organization. Editable with settings:manage.",
  user: "Belongs to one person's own preferences.",
};

/** Only organization-scoped settings can be written; see the note on `SCOPE_SYSTEM`. */
export function isEditableSetting(setting: Setting): boolean {
  return setting.scope === SCOPE_ORGANIZATION && !setting.is_secret;
}

/**
 * The value types the server infers on write (`_infer_value_type`).
 *
 * The editor asks for a type explicitly because the store is untyped: what the operator sends is
 * what the type becomes, and `"true"` as a string is a different stored value from `true`.
 */
export type ValueType = "string" | "number" | "boolean" | "json";

export const VALUE_TYPE_LABELS: Record<ValueType, string> = {
  string: "Text",
  number: "Number",
  boolean: "True / false",
  json: "JSON",
};

export const VALUE_TYPES = Object.keys(VALUE_TYPE_LABELS) as ValueType[];

/** The type a stored value already has, so the editor opens on the right control. */
export function inferValueType(value: unknown): ValueType {
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  if (typeof value === "string") return "string";
  return "json";
}

/** A key/value row as the editor holds it, before it becomes a typed JSON value. */
export interface ValueDraft {
  type: ValueType;
  /** The raw text in the control; parsed on submit according to `type`. */
  text: string;
}

export function draftFromValue(value: unknown): ValueDraft {
  const type = inferValueType(value);
  if (type === "boolean") return { type, text: value === true ? "true" : "false" };
  if (type === "json") return { type, text: JSON.stringify(value ?? null, null, 2) };
  return { type, text: String(value ?? "") };
}

export interface ParsedValue {
  ok: boolean;
  value?: unknown;
  error?: string;
}

/**
 * Turn a draft back into the JSON value to send.
 *
 * Parsing is strict on purpose: a number field that silently sent `NaN`, or a JSON field that sent
 * a string because it did not parse, would store a value the operator did not choose — and the
 * store has no schema to catch it afterwards.
 */
export function parseValue(draft: ValueDraft): ParsedValue {
  if (draft.type === "boolean") return { ok: true, value: draft.text === "true" };
  if (draft.type === "number") {
    const parsed = Number(draft.text.trim());
    if (draft.text.trim() === "" || Number.isNaN(parsed)) {
      return { ok: false, error: "Enter a number" };
    }
    return { ok: true, value: parsed };
  }
  if (draft.type === "json") {
    try {
      return { ok: true, value: JSON.parse(draft.text) };
    } catch {
      return { ok: false, error: "Not valid JSON" };
    }
  }
  return { ok: true, value: draft.text };
}

/** Settings keys are stored as `String(120)`; the store imposes no other rule. */
export const MAX_KEY_LENGTH = 120;

export function validateKey(key: string, existing: string[]): string | null {
  const trimmed = key.trim();
  if (trimmed === "") return "Key is required";
  if (trimmed.length > MAX_KEY_LENGTH) return `Keys are limited to ${MAX_KEY_LENGTH} characters`;
  if (existing.includes(trimmed)) return "That key already exists";
  return null;
}

/** Feature-flag descriptions are `String(255)` on the model and bounded in the patch schema. */
export const MAX_FLAG_DESCRIPTION = 255;
