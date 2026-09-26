import type { Template } from "@/features/campaigns/types";

/**
 * Reading a template's own structure, so the wizard can render one mapping control per placeholder.
 *
 * `TemplateResponse.components` is typed `object[]` on the wire — the contract carries the array
 * but not its interior — so the shape is interpreted here rather than declared as an API type.
 * This is **not** a second validator: the server checks that the map fills exactly the placeholders
 * the template declares and answers 422 `count_mismatch` when it does not. This only decides how
 * many controls to draw.
 */

const PLACEHOLDER = /\{\{\s*(\d+)\s*\}\}/g;

interface ComponentLike {
  type?: unknown;
  format?: unknown;
  text?: unknown;
  buttons?: unknown;
}

interface ButtonLike {
  type?: unknown;
  text?: unknown;
  url?: unknown;
  phone_number?: unknown;
  example?: unknown;
}

/** Button kinds whose value the sender supplies; the rest are settled at approval time. */
const VARIABLE_BUTTONS = new Set(["URL", "QUICK_REPLY", "COPY_CODE"]);

/**
 * The buttons a send must supply a value for: a variable-capable kind whose destination actually
 * carries a placeholder. A URL button holds its variable inside the link, so this is the only
 * place the count is visible from the template alone.
 */
export function variableButtons(template: Template | undefined): ButtonLike[] {
  if (!template) return [];
  const component = componentOf(template, "BUTTONS");
  const buttons = Array.isArray(component?.buttons) ? (component.buttons as ButtonLike[]) : [];
  return buttons.filter((button) => {
    const kind = String(button.type ?? "").toUpperCase();
    const target = button.url ?? button.phone_number ?? button.example ?? "";
    return VARIABLE_BUTTONS.has(kind) && placeholderIndices(target).length > 0;
  });
}

function componentOf(template: Template, type: string): ComponentLike | undefined {
  return (template.components as ComponentLike[]).find(
    (component) => String(component.type ?? "").toUpperCase() === type,
  );
}

/** The distinct placeholder indices a text carries, in ascending order. */
export function placeholderIndices(text: unknown): number[] {
  if (typeof text !== "string") return [];
  const found = new Set<number>();
  for (const match of text.matchAll(PLACEHOLDER)) {
    const raw = match[1];
    if (raw !== undefined) found.add(Number.parseInt(raw, 10));
  }
  return [...found].sort((a, b) => a - b);
}

export interface TemplateShape {
  /** How many header variables a send must supply — zero unless the header is a text header. */
  headerCount: number;
  bodyCount: number;
  /** How many buttons carry a variable in their destination and therefore need a mapping. */
  buttonCount: number;
  /** Those buttons' labels, so the control can say which button it is asking about. */
  buttonLabels: string[];
  headerText: string;
  bodyText: string;
  footerText: string;
  /** A non-text header carries media instead of variables (image/video/document). */
  mediaHeaderFormat: string | null;
}

export function templateShape(template: Template | undefined): TemplateShape {
  if (!template) {
    return {
      headerCount: 0,
      bodyCount: 0,
      buttonCount: 0,
      buttonLabels: [],
      headerText: "",
      bodyText: "",
      footerText: "",
      mediaHeaderFormat: null,
    };
  }

  const buttons = variableButtons(template);
  const header = componentOf(template, "HEADER");
  const body = componentOf(template, "BODY");
  const footer = componentOf(template, "FOOTER");
  const format = String(header?.format ?? "TEXT").toUpperCase();
  const isTextHeader = format === "TEXT";

  return {
    headerCount: header && isTextHeader ? placeholderIndices(header.text).length : 0,
    bodyCount: placeholderIndices(body?.text).length,
    buttonCount: buttons.length,
    buttonLabels: buttons.map((button) => String(button.text ?? "Button")),
    headerText: typeof header?.text === "string" ? header.text : "",
    bodyText: typeof body?.text === "string" ? body.text : "",
    footerText: typeof footer?.text === "string" ? footer.text : "",
    mediaHeaderFormat: header && !isTextHeader ? format : null,
  };
}

/**
 * Contact columns a variable may be mapped to.
 *
 * A whitelist on the server (`MAPPABLE_FIELDS`) — a campaign must not be able to interpolate an
 * arbitrary column into a customer's message. Listed here so the picker offers only what will be
 * accepted; the server rejects anything else regardless.
 */
export const MAPPABLE_FIELDS: { value: string; label: string }[] = [
  { value: "full_name", label: "Full name" },
  { value: "first_name", label: "First name" },
  { value: "last_name", label: "Last name" },
  { value: "phone_e164", label: "Phone (E.164)" },
  { value: "wa_id", label: "WhatsApp id" },
  { value: "email", label: "Email" },
  { value: "profile_name", label: "WhatsApp profile name" },
  { value: "locale", label: "Locale" },
  { value: "country_code", label: "Country code" },
];
