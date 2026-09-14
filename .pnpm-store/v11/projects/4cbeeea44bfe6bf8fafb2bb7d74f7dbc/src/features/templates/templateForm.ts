import type { TemplateDraft } from "@/features/templates/components";
import {
  analyzeVariables,
  MAX_BODY_CHARS,
  MAX_BUTTONS,
  MAX_FOOTER_CHARS,
  MAX_HEADER_CHARS,
  toComponents,
} from "@/features/templates/components";
import type {
  Template,
  TemplateCreateRequest,
  TemplateUpdateRequest,
} from "@/features/templates/types";

/**
 * Definition validation, mirroring `template_validation.py`.
 *
 * Doc 04 §15 validates before Meta ever sees a template precisely to cut rejection loops — a
 * rejection costs hours of round trip. Checking the same rules here moves that feedback from
 * "after submitting" to "while typing". The server re-checks everything and its 422 is what
 * decides; nothing here is trusted.
 *
 * Returned as a field→message map rather than thrown, because the editor shows several problems at
 * once and an operator fixing a template wants to see all of them.
 */
export type FieldErrors = Partial<Record<FieldKey, string>>;

export type FieldKey =
  | "waba_id"
  | "name"
  | "language"
  | "header_text"
  | "body_text"
  | "footer_text"
  | "buttons";

/** Meta's template name rule: lower-case letters, digits and underscores only. */
const NAME_PATTERN = /^[a-z0-9_]+$/;

export function validateDraft(draft: TemplateDraft, { creating }: { creating: boolean }): FieldErrors {
  const errors: FieldErrors = {};

  if (creating) {
    if (!draft.waba_id) errors.waba_id = "Choose a WhatsApp Business Account";
    const name = draft.name.trim();
    if (name === "") errors.name = "Name is required";
    else if (name.length > 512) errors.name = "Name is too long";
    else if (!NAME_PATTERN.test(name)) {
      errors.name = "Use lower-case letters, digits and underscores only (e.g. order_update)";
    }

    const language = draft.language.trim();
    if (language.length < 2 || language.length > 10) {
      errors.language = "Use a language code such as en_US";
    }
  }

  // Body: required, bounded, and the only component that may carry several variables.
  const body = draft.body_text;
  if (body.trim() === "") errors.body_text = "The body needs text";
  else if (body.length > MAX_BODY_CHARS) {
    errors.body_text = `Body may not exceed ${MAX_BODY_CHARS} characters (currently ${body.length})`;
  }

  // Header: text headers need text and allow at most one variable; media headers carry no text.
  if (draft.header_format === "text") {
    const header = draft.header_text;
    if (header.trim() === "") errors.header_text = "A text header needs text";
    else if (header.length > MAX_HEADER_CHARS) {
      errors.header_text = `Header may not exceed ${MAX_HEADER_CHARS} characters (currently ${header.length})`;
    }
  }

  if (draft.footer_text.length > MAX_FOOTER_CHARS) {
    errors.footer_text = `Footer may not exceed ${MAX_FOOTER_CHARS} characters (currently ${draft.footer_text.length})`;
  }
  if (/\{\{\s*\d+\s*\}\}/.test(draft.footer_text)) {
    errors.footer_text = "A footer cannot contain variables";
  }

  // Placeholder numbering is the load-bearing rule: Meta rejects gaps outright.
  const analysis = analyzeVariables(
    draft.header_format === "text" ? draft.header_text : "",
    draft.body_text,
  );
  if (analysis.problems.length > 0) {
    const headerProblem = analysis.problems.find((problem) => problem.startsWith("Header") || problem.startsWith("A header"));
    const bodyProblem = analysis.problems.find((problem) => problem.startsWith("Body"));
    if (headerProblem) errors.header_text = headerProblem;
    if (bodyProblem) errors.body_text = bodyProblem;
  }

  if (draft.buttons.length > MAX_BUTTONS) {
    errors.buttons = `A template may have at most ${MAX_BUTTONS} buttons`;
  } else {
    for (const [index, button] of draft.buttons.entries()) {
      if (button.text.trim() === "") {
        errors.buttons = `Button ${index + 1} needs a label`;
        break;
      }
      if (button.type === "url" && button.url.trim() === "") {
        errors.buttons = `Button ${index + 1} needs a URL`;
        break;
      }
      if (button.type === "phone_number" && button.phone_number.trim() === "") {
        errors.buttons = `Button ${index + 1} needs a phone number`;
        break;
      }
    }
  }

  return errors;
}

export function hasErrors(errors: FieldErrors): boolean {
  return Object.keys(errors).length > 0;
}

export function toCreateRequest(draft: TemplateDraft, submit: boolean): TemplateCreateRequest {
  return {
    waba_id: draft.waba_id,
    name: draft.name.trim(),
    language: draft.language.trim(),
    category: draft.category,
    components: toComponents(draft),
    submit,
  };
}

/**
 * An edit sends the category, the components and `row_version`, so a concurrent change surfaces as
 * the server's conflict rather than silently overwriting someone else's work. Name, language and
 * WABA are absent because the contract does not accept them — those identify the template.
 */
export function toUpdateRequest(
  draft: TemplateDraft,
  template: Template,
  submit: boolean,
): TemplateUpdateRequest {
  return {
    category: draft.category,
    components: toComponents(draft),
    submit,
    row_version: template.row_version,
  };
}
