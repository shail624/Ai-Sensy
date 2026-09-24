import { describe, expect, it } from "vitest";

import { markUtc } from "./utc";

describe("markUtc", () => {
  it("marks naive API date-times as UTC so they render in local time correctly", () => {
    expect(markUtc("2026-09-24T01:02:49.471787")).toBe("2026-09-24T01:02:49.471787Z");
    expect(markUtc("2026-09-24T01:02:49")).toBe("2026-09-24T01:02:49Z");
    expect(new Date(markUtc("2026-09-24T01:00:00") as string).toISOString()).toBe("2026-09-24T01:00:00.000Z");
  });

  it("leaves offsets, plain dates, clock times and other text alone", () => {
    for (const value of ["2026-09-24T01:02:49Z", "2026-09-24T01:02:49+05:30", "2026-09-24", "10:30", "hello", ""]) {
      expect(markUtc(value)).toBe(value);
    }
  });

  it("walks nested objects and arrays without touching other types", () => {
    expect(
      markUtc({ data: [{ created_at: "2026-01-01T00:00:00", count: 3, ok: true, none: null }], page: { next: null } }),
    ).toEqual({ data: [{ created_at: "2026-01-01T00:00:00Z", count: 3, ok: true, none: null }], page: { next: null } });
  });
});
