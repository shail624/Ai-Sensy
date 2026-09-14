import type {
  NumberListQuery,
  NumberSort,
  PhoneNumber,
  Waba,
  WabaListQuery,
  WabaSort,
} from "@/features/channels/types";
import { isNumberHealthy, NUMBER_STATUS_CONNECTED, tokenState } from "@/features/channels/types";

// --- WABAs --------------------------------------------------------------------------------------

const WABA_COMPARATORS: Record<WabaSort, (a: Waba, b: Waba) => number> = {
  name: (a, b) => a.business_name.localeCompare(b.business_name),
  "-name": (a, b) => b.business_name.localeCompare(a.business_name),
  "-created_at": (a, b) => Date.parse(b.created_at) - Date.parse(a.created_at),
  "-numbers": (a, b) => b.phone_number_count - a.phone_number_count,
};

/**
 * Matches the business name or Meta's WABA id.
 *
 * The id matters as much as the name here: it is what appears in Meta's own console and in support
 * tickets, so an operator cross-referencing the two has it to hand more often than the name.
 */
export function matchesWaba(waba: Waba, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return (
    waba.business_name.toLowerCase().includes(needle) ||
    waba.waba_id.toLowerCase().includes(needle) ||
    (waba.meta_business_id ?? "").toLowerCase().includes(needle)
  );
}

export function filterWabas(wabas: Waba[], query: WabaListQuery): Waba[] {
  return wabas.filter(
    (waba) => matchesWaba(waba, query.q) && (query.status === "" || waba.status === query.status),
  );
}

export function selectWabas(wabas: Waba[], query: WabaListQuery): Waba[] {
  return [...filterWabas(wabas, query)].sort(WABA_COMPARATORS[query.sort]);
}

export interface WabaSummary {
  total: number;
  active: number;
  /** Accounts whose credential is missing, expired, or close to it — the ones needing attention. */
  needsAttention: number;
  numbers: number;
}

export function wabaSummary(wabas: Waba[], now: number = Date.now()): WabaSummary {
  return {
    total: wabas.length,
    active: wabas.filter((waba) => waba.status === "active").length,
    needsAttention: wabas.filter((waba) => tokenState(waba, now) !== "ok").length,
    numbers: wabas.reduce((total, waba) => total + waba.phone_number_count, 0),
  };
}

// --- Phone numbers --------------------------------------------------------------------------------

/** Worst first, so a number Meta has flagged is the first thing on screen. */
const QUALITY_ORDER: Record<string, number> = { RED: 0, YELLOW: 1, GREEN: 2 };

function qualityRank(number: PhoneNumber): number {
  // An unrated number sorts after every rated one: absent is not "good", it is unknown.
  return number.quality_rating ? (QUALITY_ORDER[number.quality_rating] ?? 3) : 4;
}

const NUMBER_COMPARATORS: Record<NumberSort, (a: PhoneNumber, b: PhoneNumber) => number> = {
  number: (a, b) => a.display_number.localeCompare(b.display_number),
  "-number": (a, b) => b.display_number.localeCompare(a.display_number),
  "-quality": (a, b) => qualityRank(a) - qualityRank(b),
  "-mps_limit": (a, b) => b.mps_limit - a.mps_limit,
};

export function matchesNumber(number: PhoneNumber, q: string): boolean {
  const needle = q.trim().toLowerCase();
  if (!needle) return true;
  return (
    number.display_number.toLowerCase().includes(needle) ||
    (number.verified_name ?? "").toLowerCase().includes(needle) ||
    number.phone_number_id.toLowerCase().includes(needle)
  );
}

export function filterNumbers(numbers: PhoneNumber[], query: NumberListQuery): PhoneNumber[] {
  return numbers.filter(
    (number) =>
      matchesNumber(number, query.q) &&
      (query.waba === "" || number.waba_id === query.waba) &&
      (query.status === "" || number.status === query.status) &&
      (query.quality === "" || number.quality_rating === query.quality),
  );
}

export function selectNumbers(numbers: PhoneNumber[], query: NumberListQuery): PhoneNumber[] {
  return [...filterNumbers(numbers, query)].sort(NUMBER_COMPARATORS[query.sort]);
}

/**
 * The status values actually present.
 *
 * A number's `status` is an unconstrained string that Meta's sync writes into, so a fixed list
 * would go stale the first time Meta introduces a value. Deriving the options from the data keeps
 * the filter honest — and `connected` is included even when nothing holds it, because it is the
 * column default and an operator will look for it.
 */
export function numberStatuses(numbers: PhoneNumber[]): string[] {
  const present = new Set(numbers.map((number) => number.status));
  present.add(NUMBER_STATUS_CONNECTED);
  return [...present].sort();
}

export interface NumberSummary {
  total: number;
  connected: number;
  healthy: number;
  /** Rated RED by Meta — restricted or at risk of being restricted. */
  degraded: number;
  /** Total per-second send pacing across every connected number. */
  capacity: number;
}

export function numberSummary(numbers: PhoneNumber[]): NumberSummary {
  return {
    total: numbers.length,
    connected: numbers.filter((number) => number.status === NUMBER_STATUS_CONNECTED).length,
    healthy: numbers.filter(isNumberHealthy).length,
    degraded: numbers.filter((number) => number.quality_rating === "RED").length,
    capacity: numbers
      .filter((number) => number.status === NUMBER_STATUS_CONNECTED)
      .reduce((total, number) => total + number.mps_limit, 0),
  };
}

/** The numbers belonging to one account, in the list's own order. */
export function numbersForWaba(numbers: PhoneNumber[], wabaId: string): PhoneNumber[] {
  return numbers.filter((number) => number.waba_id === wabaId);
}
