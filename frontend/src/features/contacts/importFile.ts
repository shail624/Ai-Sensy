import type { AttributeDefinition } from "@/features/contacts/types";

/** Mapping targets that land on a contact column; anything else must be `attr.<key>` (Doc 04). */
export const CONTACT_FIELDS = [
  "phone_e164",
  "full_name",
  "first_name",
  "last_name",
  "email",
  "locale",
  "country_code",
  "opt_in_status",
] as const;

export const FIELD_LABELS: Record<string, string> = {
  phone_e164: "Phone (E.164)",
  full_name: "Full name",
  first_name: "First name",
  last_name: "Last name",
  email: "Email",
  locale: "Locale",
  country_code: "Country code",
  opt_in_status: "Opt-in status",
};

/** The one target the server insists on — an import without it is rejected. */
export const REQUIRED_TARGET = "phone_e164";

/** Sentinel for "do not import this column". Never sent: skipped columns leave the mapping. */
export const SKIP = "";

export const ATTR_PREFIX = "attr.";

/** Read the whole file only when it is small enough to stay instant; bigger files preview a slice. */
export const FULL_READ_LIMIT = 5 * 1024 * 1024;
/** The server's ceiling for a `document` upload. */
export const MAX_UPLOAD_BYTES = 100 * 1024 * 1024;

export interface CsvPreview {
  headers: string[];
  rows: string[][];
  /** Data rows in the file, or `null` when only a slice was read. */
  rowCount: number | null;
  truncated: boolean;
}

/**
 * Split CSV text into records, honouring quoted fields (which may contain commas and newlines) and
 * the doubled-quote escape. Written out rather than pulled from a library: the wizard needs headers
 * and a handful of preview rows, and the parse budget is one pass with no dependency.
 */
export function parseCsv(text: string, maxRecords = Number.POSITIVE_INFINITY): string[][] {
  const records: string[][] = [];
  let field = "";
  let record: string[] = [];
  let quoted = false;
  let started = false;

  const pushField = (): void => {
    record.push(field);
    field = "";
  };
  const pushRecord = (): void => {
    pushField();
    // A trailing newline produces one empty field — that is not a record.
    if (record.length > 1 || record[0] !== "") records.push(record);
    record = [];
    started = false;
  };

  const source = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text; // strip the BOM

  for (let i = 0; i < source.length; i += 1) {
    const char = source[i]!;
    if (quoted) {
      if (char === '"') {
        if (source[i + 1] === '"') {
          field += '"';
          i += 1;
        } else {
          quoted = false;
        }
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"' && !started) {
      quoted = true;
      started = true;
      continue;
    }
    if (char === ",") {
      pushField();
      started = false;
      continue;
    }
    if (char === "\r") continue;
    if (char === "\n") {
      pushRecord();
      if (records.length >= maxRecords) return records;
      continue;
    }
    field += char;
    started = true;
  }
  if (field !== "" || record.length > 0) pushRecord();
  return records;
}

/** Headers plus the first rows, for the mapping preview. */
export function readPreview(text: string, options: { complete: boolean; maxRows?: number }): CsvPreview {
  const maxRows = options.maxRows ?? 5;
  const records = parseCsv(text, options.complete ? Number.POSITIVE_INFINITY : maxRows + 1);
  const [headers = [], ...rows] = records;
  return {
    headers,
    rows: rows.slice(0, maxRows),
    rowCount: options.complete ? rows.length : null,
    truncated: !options.complete,
  };
}

/** Compare headers ignoring case, spacing and punctuation, so "Phone Number" matches "phone_number". */
function normalize(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]/g, "");
}

const SYNONYMS: Record<string, string> = {
  phone: "phone_e164",
  phonenumber: "phone_e164",
  phonee164: "phone_e164",
  mobile: "phone_e164",
  mobilenumber: "phone_e164",
  msisdn: "phone_e164",
  whatsapp: "phone_e164",
  whatsappnumber: "phone_e164",
  waid: "phone_e164",
  number: "phone_e164",
  name: "full_name",
  fullname: "full_name",
  customername: "full_name",
  contactname: "full_name",
  firstname: "first_name",
  givenname: "first_name",
  lastname: "last_name",
  surname: "last_name",
  familyname: "last_name",
  email: "email",
  emailaddress: "email",
  mail: "email",
  locale: "locale",
  language: "locale",
  country: "country_code",
  countrycode: "country_code",
  optin: "opt_in_status",
  optinstatus: "opt_in_status",
  consent: "opt_in_status",
  subscribed: "opt_in_status",
};

/**
 * Guess a mapping from the file's headers: exact contact fields first, then well-known synonyms,
 * then any custom attribute whose key or label matches. Anything unrecognised stays unmapped, so a
 * wrong guess is never smuggled past the review step.
 */
export function autoMap(
  headers: string[],
  definitions: AttributeDefinition[],
): Record<string, string> {
  const byNormalizedField = new Map(CONTACT_FIELDS.map((field) => [normalize(field), field]));
  const byAttribute = new Map<string, string>();
  for (const definition of definitions) {
    byAttribute.set(normalize(definition.key_name), `${ATTR_PREFIX}${definition.key_name}`);
    byAttribute.set(normalize(definition.label), `${ATTR_PREFIX}${definition.key_name}`);
  }

  const mapping: Record<string, string> = {};
  const taken = new Set<string>();
  for (const header of headers) {
    const key = normalize(header);
    const guess = byNormalizedField.get(key) ?? SYNONYMS[key] ?? byAttribute.get(key) ?? SKIP;
    // A contact column can only be filled once; a second candidate stays unmapped.
    if (guess !== SKIP && !taken.has(guess)) {
      mapping[header] = guess;
      taken.add(guess);
    } else {
      mapping[header] = SKIP;
    }
  }
  return mapping;
}

/** Drop the skipped columns — the server validates every value it is given. */
export function toRequestMapping(mapping: Record<string, string>): Record<string, string> {
  return Object.fromEntries(Object.entries(mapping).filter(([, target]) => target !== SKIP));
}

/** The mapping is only startable once a phone column is chosen (the server's own rule). */
export function mappingIsValid(mapping: Record<string, string>): boolean {
  return Object.values(mapping).includes(REQUIRED_TARGET);
}

/** Human-readable size, for the upload and review steps. */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
