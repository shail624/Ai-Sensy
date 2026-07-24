import { describe, expect, it } from "vitest";

import {
  autoMap,
  formatBytes,
  mappingIsValid,
  parseCsv,
  readPreview,
  toRequestMapping,
} from "@/features/contacts/importFile";
import type { AttributeDefinition } from "@/features/contacts/types";

const DEFINITIONS = [
  {
    id: "a1",
    type: "custom_attribute",
    key_name: "reactivation_status",
    label: "Reactivation status",
    data_type: "enum",
    enum_values: ["pending"],
    is_indexed: true,
    is_pii: false,
    created_at: "",
    updated_at: "",
  },
] as AttributeDefinition[];

describe("parseCsv", () => {
  it("splits plain records", () => {
    expect(parseCsv("a,b\n1,2\n3,4")).toEqual([
      ["a", "b"],
      ["1", "2"],
      ["3", "4"],
    ]);
  });

  it("keeps commas and newlines inside quoted fields", () => {
    expect(parseCsv('name,note\n"Sharma, Priya","line one\nline two"')).toEqual([
      ["name", "note"],
      ["Sharma, Priya", "line one\nline two"],
    ]);
  });

  it("unescapes doubled quotes", () => {
    expect(parseCsv('a\n"say ""hi"""')).toEqual([["a"], ['say "hi"']]);
  });

  it("tolerates CRLF, a BOM and a trailing newline", () => {
    expect(parseCsv("﻿a,b\r\n1,2\r\n")).toEqual([
      ["a", "b"],
      ["1", "2"],
    ]);
  });

  it("stops at the record limit", () => {
    expect(parseCsv("a\n1\n2\n3\n", 2)).toHaveLength(2);
  });
});

describe("readPreview", () => {
  it("returns headers, sample rows and a row count for a complete read", () => {
    const preview = readPreview("phone,name\n+1,A\n+2,B\n", { complete: true });
    expect(preview.headers).toEqual(["phone", "name"]);
    expect(preview.rows).toEqual([
      ["+1", "A"],
      ["+2", "B"],
    ]);
    expect(preview.rowCount).toBe(2);
    expect(preview.truncated).toBe(false);
  });

  it("reports no row count when only a slice was read", () => {
    const preview = readPreview("phone\n+1\n", { complete: false });
    expect(preview.rowCount).toBeNull();
    expect(preview.truncated).toBe(true);
  });
});

describe("autoMap", () => {
  it("matches exact fields, synonyms and custom attributes", () => {
    expect(
      autoMap(["Phone Number", "Full Name", "E-mail", "Reactivation status"], DEFINITIONS),
    ).toEqual({
      "Phone Number": "phone_e164",
      "Full Name": "full_name",
      "E-mail": "email",
      "Reactivation status": "attr.reactivation_status",
    });
  });

  it("leaves a column unmapped rather than guessing twice at the same target", () => {
    const mapping = autoMap(["phone", "mobile"], []);
    expect(mapping.phone).toBe("phone_e164");
    expect(mapping.mobile).toBe("");
  });

  it("leaves unknown columns unmapped", () => {
    expect(autoMap(["loyalty tier"], [])).toEqual({ "loyalty tier": "" });
  });
});

describe("mapping helpers", () => {
  it("requires a phone target", () => {
    expect(mappingIsValid({ a: "full_name" })).toBe(false);
    expect(mappingIsValid({ a: "phone_e164" })).toBe(true);
  });

  it("drops skipped columns from the request", () => {
    expect(toRequestMapping({ a: "phone_e164", b: "", c: "email" })).toEqual({
      a: "phone_e164",
      c: "email",
    });
  });
});

describe("formatBytes", () => {
  it("scales the unit", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});
