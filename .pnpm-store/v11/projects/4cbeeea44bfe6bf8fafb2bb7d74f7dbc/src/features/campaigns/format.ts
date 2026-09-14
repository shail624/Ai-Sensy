/** Shown wherever a value is genuinely unknown rather than zero. */
export const UNKNOWN = "—";

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined) return UNKNOWN;
  return value.toLocaleString();
}

export function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined) return UNKNOWN;
  return `${(value * 100).toFixed(1)}%`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return UNKNOWN;
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? UNKNOWN : parsed.toLocaleString();
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return UNKNOWN;
  const parsed = new Date(iso);
  return Number.isNaN(parsed.getTime()) ? UNKNOWN : parsed.toLocaleDateString();
}

/**
 * Campaign money is a **fixed-scale decimal string** on the wire, never a number (Doc 04 §17: a
 * JSON number carries no scale and lands in a binary float, which is the one representation money
 * must not pass through). So it is rendered as received — grouped for readability, but never
 * parsed into a float and re-formatted, because that would discard the scale the server chose.
 *
 * This is deliberately *not* the analytics module's `formatMicros`: that path carries integer
 * micro-units, this one carries decimal strings, and conflating them would corrupt one of them.
 */
export function formatMoney(amount: string | null | undefined, currency?: string): string {
  if (amount === null || amount === undefined || amount === "") return UNKNOWN;

  const negative = amount.startsWith("-");
  const bare = negative ? amount.slice(1) : amount;
  const [whole = "", fraction] = bare.split(".");
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  const rendered = `${negative ? "-" : ""}${grouped}${fraction ? `.${fraction}` : ""}`;
  return currency ? `${rendered} ${currency}` : rendered;
}
