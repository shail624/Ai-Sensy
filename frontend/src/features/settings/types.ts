import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written (Doc 14 §2 decoupling contract).
export type Organization = components["schemas"]["OrganizationResponse"];
export type OrganizationUpdateRequest = components["schemas"]["OrganizationUpdateRequest"];
export type Setting = components["schemas"]["SettingResponse"];
export type SettingsUpdateRequest = components["schemas"]["SettingsUpdateRequest"];
export type FeatureFlag = components["schemas"]["FeatureFlagResponse"];
export type FeatureFlagPatchRequest = components["schemas"]["FeatureFlagPatchRequest"];
export type Preferences = components["schemas"]["PreferencesResponse"];
export type Tag = components["schemas"]["TagResponse"];
export type TagCreateRequest = components["schemas"]["TagCreateRequest"];
export type TagUpdateRequest = components["schemas"]["TagUpdateRequest"];
export type QuickReply = components["schemas"]["QuickReplyResponse"];
export type QuickReplyCreateRequest = components["schemas"]["QuickReplyCreateRequest"];
export type QuickReplyUpdateRequest = components["schemas"]["QuickReplyUpdateRequest"];

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

/** Tag bounds, mirrored from `schemas/tag.py` so the form fails before a pointless round-trip. */
export const MAX_TAG_NAME = 60;
export const MAX_TAG_DESCRIPTION = 255;

/** The server accepts `#RRGGBB` only, or no colour at all. */
const TAG_COLOR_PATTERN = /^#[0-9a-fA-F]{6}$/;

export function validateTagName(name: string): string | null {
  const trimmed = name.trim();
  if (trimmed === "") return "Name is required";
  if (trimmed.length > MAX_TAG_NAME) return `Names are limited to ${MAX_TAG_NAME} characters`;
  return null;
}

/**
 * An empty colour is valid and means "no colour" — the column is nullable, so a tag without one is
 * a real state rather than an incomplete form.
 */
export function validateTagColor(color: string): string | null {
  const trimmed = color.trim();
  if (trimmed === "") return null;
  if (!TAG_COLOR_PATTERN.test(trimmed)) return "Use a hex colour such as #1F6FEB";
  return null;
}

export function validateTagDescription(description: string): string | null {
  if (description.length > MAX_TAG_DESCRIPTION) {
    return `Descriptions are limited to ${MAX_TAG_DESCRIPTION} characters`;
  }
  return null;
}

/** Tags carry no status field, so "in use" is derived from the usage count the read returns. */
export type TagUsageFilter = "all" | "used" | "unused";

export function matchesTagFilter(tag: Tag, search: string, usage: TagUsageFilter): boolean {
  if (usage === "used" && tag.usage_count === 0) return false;
  if (usage === "unused" && tag.usage_count > 0) return false;

  const term = search.trim().toLowerCase();
  if (term === "") return true;
  return (
    tag.name.toLowerCase().includes(term) ||
    (tag.description ?? "").toLowerCase().includes(term)
  );
}

/** Quick-reply bounds, mirrored from `schemas/quick_reply.py` (Doc 04 §18.2). */
export const MAX_SHORTCUT = 60;
export const MAX_TITLE = 120;
export const MAX_BODY = 4096;

export function validateShortcut(shortcut: string): string | null {
  const trimmed = shortcut.trim();
  if (trimmed === "") return "Shortcut is required";
  if (trimmed.length > MAX_SHORTCUT) return `Shortcuts are limited to ${MAX_SHORTCUT} characters`;
  return null;
}

export function validateTitle(title: string): string | null {
  const trimmed = title.trim();
  if (trimmed === "") return "Title is required";
  if (trimmed.length > MAX_TITLE) return `Titles are limited to ${MAX_TITLE} characters`;
  return null;
}

export function validateBody(body: string): string | null {
  const trimmed = body.trim();
  if (trimmed === "") return "Body is required";
  if (trimmed.length > MAX_BODY) return `Bodies are limited to ${MAX_BODY} characters`;
  return null;
}

/**
 * Quick replies carry no status field either; the operationally useful split is who can see one —
 * `shared` is fixed at creation, so this is also the only axis edit never needs to change.
 */
export type QuickReplyScopeFilter = "all" | "personal" | "shared";

export function matchesQuickReplyFilter(
  reply: QuickReply,
  search: string,
  scope: QuickReplyScopeFilter,
): boolean {
  if (scope === "personal" && reply.shared) return false;
  if (scope === "shared" && !reply.shared) return false;

  const term = search.trim().toLowerCase();
  if (term === "") return true;
  return (
    reply.shortcut.toLowerCase().includes(term) ||
    reply.title.toLowerCase().includes(term) ||
    reply.body.toLowerCase().includes(term)
  );
}

/** A one-line table preview — the full body belongs in the editor, not the row. */
export function previewQuickReplyBody(body: string, maxLength = 80): string {
  const collapsed = body.replace(/\s+/g, " ").trim();
  return collapsed.length > maxLength ? `${collapsed.slice(0, maxLength - 1)}…` : collapsed;
}
