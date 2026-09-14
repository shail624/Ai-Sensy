import { placeholderIndices } from "@/features/campaigns/templateShape";
import type { Template, TemplateCreateRequest } from "@/features/templates/types";
import { CATEGORIES } from "@/features/templates/types";

/**
 * The template component model — reading a definition, editing it, and turning it back into the
 * wire shape.
 *
 * `components` is typed `object[]` in the contract: the array is declared but its interior is not,
 * because it is the platform's own structure rather than a Graph payload. So the interior is
 * modelled here as **form state**, and mapped to and from the wire in one place.
 *
 * The limits and rules below mirror `template_validation.py` so an operator learns about a problem
 * before a round trip — Doc 04 §15 validates before Meta ever sees it precisely to cut rejection
 * loops. The server re-checks all of it and its 422 is what decides.
 *
 * `placeholderIndices` is imported rather than reimplemented: how the platform counts `{{n}}` is one
 * rule, and the campaign wizard already depends on it. (The dependency points the wrong way — it
 * belongs in a shared module — but pointing it correctly means editing the campaigns feature, which
 * this milestone must not touch.)
 */

// Meta's structural limits, as `template_validation.py` states them.
export const MAX_BODY_CHARS = 1024;
export const MAX_HEADER_CHARS = 60;
export const MAX_FOOTER_CHARS = 60;
export const MAX_BUTTONS = 10;
export const MAX_HEADER_VARIABLES = 1;

export type HeaderFormat = "none" | "text" | "image" | "video" | "document" | "location";
export type ButtonType = "quick_reply" | "url" | "phone_number" | "copy_code";

export const HEADER_FORMAT_LABELS: Record<HeaderFormat, string> = {
  none: "No header",
  text: "Text",
  image: "Image",
  video: "Video",
  document: "Document",
  location: "Location",
};

export const HEADER_FORMATS = Object.keys(HEADER_FORMAT_LABELS) as HeaderFormat[];

/** Header formats that carry a file rather than text (`MEDIA_FORMATS`). */
export const MEDIA_FORMATS: HeaderFormat[] = ["image", "video", "document"];

export const BUTTON_TYPE_LABELS: Record<ButtonType, string> = {
  quick_reply: "Quick reply",
  url: "Visit website",
  phone_number: "Call phone number",
  copy_code: "Copy code",
};

export const BUTTON_TYPES = Object.keys(BUTTON_TYPE_LABELS) as ButtonType[];

export interface ButtonDraft {
  type: ButtonType;
  text: string;
  url: string;
  phone_number: string;
}

/** A template definition as the editor holds it — flat, so each control binds to one field. */
export interface TemplateDraft {
  waba_id: string;
  name: string;
  language: string;
  category: TemplateCreateRequest["category"];
  header_format: HeaderFormat;
  header_text: string;
  body_text: string;
  footer_text: string;
  buttons: ButtonDraft[];
}

export function blankButton(): ButtonDraft {
  return { type: "quick_reply", text: "", url: "", phone_number: "" };
}

export function blankDraft(): TemplateDraft {
  return {
    waba_id: "",
    name: "",
    language: "en_US",
    category: "marketing",
    header_format: "none",
    header_text: "",
    body_text: "",
    footer_text: "",
    buttons: [],
  };
}

// --- Reading a stored definition ----------------------------------------------------------------

interface ComponentLike {
  type?: unknown;
  format?: unknown;
  text?: unknown;
  buttons?: unknown;
}

function str(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/** Component lookup is case-insensitive: Meta returns upper case, the platform stores lower. */
export function componentOf(components: unknown, kind: string): ComponentLike | undefined {
  if (!Array.isArray(components)) return undefined;
  return (components as ComponentLike[]).find(
    (component) => str(component.type).toLowerCase() === kind,
  );
}

function readButtons(components: unknown): ButtonDraft[] {
  const raw = componentOf(components, "buttons")?.buttons;
  if (!Array.isArray(raw)) return [];
  return (raw as Record<string, unknown>[]).map((button) => {
    const type = str(button.type).toLowerCase();
    return {
      type: (BUTTON_TYPES as string[]).includes(type) ? (type as ButtonType) : "quick_reply",
      text: str(button.text),
      url: str(button.url),
      phone_number: str(button.phone_number),
    };
  });
}

/** Form values from a stored template, tolerating anything unexpected in the free-form array. */
export function draftFromTemplate(template: Template): TemplateDraft {
  const header = componentOf(template.components, "header");
  const rawFormat = str(header?.format).toLowerCase();
  const headerFormat: HeaderFormat = !header
    ? "none"
    : (HEADER_FORMATS as string[]).includes(rawFormat)
      ? (rawFormat as HeaderFormat)
      : "text";

  return {
    waba_id: template.waba_id,
    name: template.name,
    language: template.language,
    category: (CATEGORIES as string[]).includes(template.category)
      ? (template.category as TemplateCreateRequest["category"])
      : "marketing",
    header_format: headerFormat,
    header_text: str(header?.text),
    body_text: str(componentOf(template.components, "body")?.text),
    footer_text: str(componentOf(template.components, "footer")?.text),
    buttons: readButtons(template.components),
  };
}

/** A clone is the source definition under a new name, as a fresh draft on the same WABA. */
export function cloneDraft(template: Template): TemplateDraft {
  return { ...draftFromTemplate(template), name: `${template.name}_copy` };
}

// --- Writing the wire shape ---------------------------------------------------------------------

/**
 * The draft as the platform's component array.
 *
 * Only the components the definition actually uses are emitted — an empty footer is absent rather
 * than present-and-blank, because the validator treats a present component as one that must be
 * valid. A media header carries no text: Meta rejects the combination outright.
 */
export function toComponents(draft: TemplateDraft): TemplateCreateRequest["components"] {
  const components: Record<string, unknown>[] = [];

  if (draft.header_format !== "none") {
    const isText = draft.header_format === "text";
    components.push(
      isText
        ? { type: "header", format: "text", text: draft.header_text.trim() }
        : { type: "header", format: draft.header_format },
    );
  }

  components.push({ type: "body", text: draft.body_text });

  if (draft.footer_text.trim() !== "") {
    components.push({ type: "footer", text: draft.footer_text.trim() });
  }

  if (draft.buttons.length > 0) {
    components.push({
      type: "buttons",
      buttons: draft.buttons.map((button) => {
        const base: Record<string, unknown> = { type: button.type, text: button.text.trim() };
        if (button.type === "url") base.url = button.url.trim();
        if (button.type === "phone_number") base.phone_number = button.phone_number.trim();
        return base;
      }),
    });
  }

  return components;
}

// --- Variable analysis --------------------------------------------------------------------------

export interface VariableUse {
  /** The `{{n}}` index, as written. */
  index: number;
  component: "header" | "body";
  /** How many times this index appears in that component's text. */
  occurrences: number;
}

export interface VariableAnalysis {
  header: VariableUse[];
  body: VariableUse[];
  /** Total distinct values a send must supply — the server's `variable_count`. */
  total: number;
  /** Numbering problems Meta would reject, per component. */
  problems: string[];
}

function occurrencesOf(text: string, index: number): number {
  return [...text.matchAll(/\{\{\s*(\d+)\s*\}\}/g)].filter(
    (match) => Number.parseInt(match[1] ?? "", 10) === index,
  ).length;
}

function usesIn(text: string, component: "header" | "body"): VariableUse[] {
  return placeholderIndices(text).map((index) => ({
    index,
    component,
    occurrences: occurrencesOf(text, index),
  }));
}

/**
 * Every variable a definition declares, where it is used, and whether the numbering is legal.
 *
 * Meta numbers variables from `{{1}}` with no gaps and rejects anything else, so a gap is reported
 * as a problem rather than silently counted.
 */
export function analyzeVariables(headerText: string, bodyText: string): VariableAnalysis {
  const header = usesIn(headerText, "header");
  const body = usesIn(bodyText, "body");
  const problems: string[] = [];

  for (const [label, uses] of [
    ["Header", header],
    ["Body", body],
  ] as const) {
    const indices = uses.map((use) => use.index);
    if (indices.length === 0) continue;
    const expected = Array.from({ length: indices.length }, (_, position) => position + 1);
    if (indices.join(",") !== expected.join(",")) {
      problems.push(
        `${label} variables must be numbered from {{1}} with no gaps; found ${indices
          .map((index) => `{{${index}}}`)
          .join(", ")}.`,
      );
    }
  }

  if (header.length > MAX_HEADER_VARIABLES) {
    problems.push(`A header may contain at most ${MAX_HEADER_VARIABLES} variable.`);
  }

  return { header, body, total: header.length + body.length, problems };
}

/** The variable analysis for a stored template, read from its components. */
export function analyzeTemplate(template: Template): VariableAnalysis {
  const header = componentOf(template.components, "header");
  const isTextHeader = str(header?.format).toLowerCase() === "text" || (header && !header.format);
  return analyzeVariables(isTextHeader ? str(header?.text) : "", str(componentOf(template.components, "body")?.text));
}

/** The media kind a header carries, or `null` for a text header or no header at all. */
export function mediaHeaderFormat(template: Template): HeaderFormat | null {
  const header = componentOf(template.components, "header");
  if (!header) return null;
  const format = str(header.format).toLowerCase() as HeaderFormat;
  return MEDIA_FORMATS.includes(format) ? format : null;
}

export function templateButtons(template: Template): ButtonDraft[] {
  return readButtons(template.components);
}
