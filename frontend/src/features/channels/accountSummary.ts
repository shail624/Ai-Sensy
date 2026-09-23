import { NUMBER_STATUS_CONNECTED, type PhoneNumber, type Waba } from "./types";

export type ApiStatus = "live" | "pending" | "not_connected";

export interface AccountSummary {
  status: ApiStatus;
  /** The business shown in the header — the first active account, else the first one held. */
  businessName: string | null;
  waba: Waba | null;
  /** The default number, else the first connected one, else any. */
  number: PhoneNumber | null;
}

/**
 * One headline answer to "can this workspace send on WhatsApp right now?", derived only from
 * stored WABA and number records — the same facts the Channels screens show in detail.
 */
export function summarizeAccount(wabas: Waba[], numbers: PhoneNumber[]): AccountSummary {
  const waba = wabas.find((candidate) => candidate.status === "active") ?? wabas[0] ?? null;
  const own = waba ? numbers.filter((candidate) => candidate.waba_id === waba.id) : numbers;
  const pool = own.length > 0 ? own : numbers;
  const number =
    pool.find((candidate) => candidate.is_default) ??
    pool.find((candidate) => candidate.status === NUMBER_STATUS_CONNECTED) ??
    pool[0] ??
    null;
  let status: ApiStatus = "not_connected";
  if (waba) {
    status =
      waba.status === "active" && numbers.some((candidate) => candidate.status === NUMBER_STATUS_CONNECTED)
        ? "live"
        : "pending";
  }
  return { status, businessName: waba?.business_name ?? null, waba, number };
}

export const API_STATUS_LABELS: Record<ApiStatus, string> = {
  live: "LIVE",
  pending: "PENDING",
  not_connected: "NOT CONNECTED",
};

/** AiSensy-style quality words: High / Medium / Low, from Meta's GREEN / YELLOW / RED. */
export const QUALITY_WORDS: Record<string, string> = {
  GREEN: "High",
  YELLOW: "Medium",
  RED: "Low",
  UNKNOWN: "Not rated",
};

/** Customers a number may start conversations with per 24h, by Meta messaging tier. */
export const TIER_LIMITS: Record<string, string> = {
  TIER_50: "50",
  TIER_250: "250",
  TIER_1K: "1,000",
  TIER_10K: "10,000",
  TIER_100K: "1,00,000",
  TIER_UNLIMITED: "Unlimited",
};
