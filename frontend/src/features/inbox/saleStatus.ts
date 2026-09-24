/** Where the sale stands with a customer — the values the server's `sale_status` accepts. */
export type SaleStatus =
  | "follow_up"
  | "sale_reminder"
  | "sale_in_field"
  | "sale_confirmed"
  | "sale_done"
  | "activated_elsewhere"
  | "not_interested";

export interface SaleStatusOption {
  value: SaleStatus;
  label: string;
  /** Tailwind classes for the coloured pill. */
  pill: string;
}

export const SALE_STATUS_OPTIONS: SaleStatusOption[] = [
  { value: "follow_up", label: "Follow-up", pill: "bg-[#e8f0fe] text-[#1a56db]" },
  { value: "sale_reminder", label: "Sale reminder", pill: "bg-[#fff4e0] text-[#b45309]" },
  { value: "sale_in_field", label: "Sale in field", pill: "bg-[#f3e8ff] text-[#7e22ce]" },
  { value: "sale_confirmed", label: "Sale confirmed", pill: "bg-[#dcfce7] text-[#15803d]" },
  { value: "sale_done", label: "Sale done", pill: "bg-[#15803d] text-white" },
  { value: "activated_elsewhere", label: "Activated from other", pill: "bg-[#e5e7eb] text-[#374151]" },
  { value: "not_interested", label: "Not interested", pill: "bg-[#fee2e2] text-[#b91c1c]" },
];

export function saleStatusOption(value: string | null | undefined): SaleStatusOption | undefined {
  return SALE_STATUS_OPTIONS.find((option) => option.value === value);
}

export function isSaleStatus(value: string | null): value is SaleStatus {
  return SALE_STATUS_OPTIONS.some((option) => option.value === value);
}

/** "5 Oct 2026" for a server `YYYY-MM-DD` date, without a timezone shift. */
export function formatDay(day: string): string {
  const [year = 1970, month = 1, date = 1] = day.split("-").map(Number);
  return new Date(year, month - 1, date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" });
}
