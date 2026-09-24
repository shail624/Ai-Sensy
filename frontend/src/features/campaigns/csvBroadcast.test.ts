import { describe, expect, it } from "vitest";

import { parseNumbersCsv } from "./CampaignTypeDialog";

describe("parseNumbersCsv", () => {
  it("reads the phone and name columns from a file with a header", () => {
    expect(parseNumbersCsv("Name,Mobile Number\nRavi,9876543210\n\"Priya\",+91 98910 00010\n")).toEqual([
      { phone: "9876543210", name: "Ravi" },
      { phone: "+91 98910 00010", name: "Priya" },
    ]);
  });

  it("reads a bare list of numbers", () => {
    expect(parseNumbersCsv("9876543210\r\n9891000010")).toEqual([
      { phone: "9876543210", name: null },
      { phone: "9891000010", name: null },
    ]);
  });

  it("returns nothing for an empty file", () => {
    expect(parseNumbersCsv("\n\n")).toEqual([]);
  });
});
