import { Link } from "react-router-dom";

import { InfoTooltip, Skeleton } from "@/components/ui";
import { QUALITY_EXPLANATIONS } from "@/features/channels/types";
import {
  API_STATUS_LABELS,
  QUALITY_WORDS,
  TIER_LIMITS,
  type AccountSummary,
} from "@/features/channels/accountSummary";

import { DASH_CARD, DASH_PRIMARY_BUTTON } from "./dashboardStyles";

const PILL = "inline-flex h-6 items-center rounded-2xl px-3 text-[13px] font-semibold leading-none text-white";

const QUALITY_PILL: Record<string, string> = {
  GREEN: "bg-[#28c152]",
  YELLOW: "bg-[#f5a623]",
  RED: "bg-[#e5484d]",
};

function Heading({ label, lines }: { label: string; lines: string[] }): JSX.Element {
  return (
    <h3 className="flex items-center gap-2 text-sm font-normal leading-[23px] text-text-primary">
      {label}
      <InfoTooltip label={`About ${label}`} lines={lines} />
    </h3>
  );
}

interface AccountStatusCardProps {
  summary: AccountSummary | null;
  loading: boolean;
  canManage: boolean;
}

/** AiSensy's first card: API status, quality rating and the sending allowance, side by side. */
export function AccountStatusCard({ summary, loading, canManage }: AccountStatusCardProps): JSX.Element {
  if (loading) {
    return (
      <section aria-label="WhatsApp account status" className={`${DASH_CARD} px-8 py-6`}>
        <Skeleton className="h-14 w-full" />
      </section>
    );
  }

  const status = summary?.status ?? "not_connected";
  const quality = summary?.number?.quality_rating ?? null;
  const tier = summary?.number?.messaging_tier ?? null;
  const limit = tier ? TIER_LIMITS[tier] ?? tier : null;
  const statusLines =
    status === "live"
      ? ["WhatsApp Business API is live!", ...(limit ? [`${limit} daily messaging limit.`] : [])]
      : status === "pending"
        ? ["Account connected.", "Waiting for a connected WhatsApp number before sending."]
        : ["No WhatsApp Business account is connected.", "Connect one to start sending messages."];

  return (
    <section aria-label="WhatsApp account status" className={`${DASH_CARD} grid gap-6 px-8 py-6 sm:grid-cols-3`}>
      <div>
        <Heading label="WhatsApp Business API Status" lines={statusLines} />
        <div className="mt-2 flex items-center gap-3">
          <span className={`${PILL} ${status === "live" ? "bg-[#28c152]" : status === "pending" ? "bg-[#f5a623]" : "bg-[#9e9e9e]"}`}>
            {API_STATUS_LABELS[status]}
          </span>
          {status === "not_connected" && canManage ? (
            <Link to="/channels/accounts" className={DASH_PRIMARY_BUTTON}>Connect</Link>
          ) : null}
        </div>
      </div>
      <div>
        <Heading
          label="Quality Rating"
          lines={[quality ? QUALITY_EXPLANATIONS[quality] ?? quality : "Shown once a WhatsApp number is connected.", "Low quality can reduce your messaging limit."]}
        />
        <div className="mt-2">
          {quality && QUALITY_PILL[quality] ? (
            <span className={`${PILL} ${QUALITY_PILL[quality]}`}>{QUALITY_WORDS[quality]}</span>
          ) : (
            <span className={`${PILL} bg-[#9e9e9e]`}>{quality ? QUALITY_WORDS[quality] ?? quality : "—"}</span>
          )}
        </div>
      </div>
      <div>
        <Heading label="Messaging Limit" lines={["New customers you can message in 24 hours.", "Meta raises it while your quality stays high."]} />
        <p className="mt-2 text-xl leading-[23px] text-[var(--color-nav-bg)] dark:text-accent">
          {limit ?? "—"}
          {tier && tier !== "TIER_UNLIMITED" ? <span className="ml-1 text-xs text-text-secondary">/ 24h</span> : null}
        </p>
      </div>
    </section>
  );
}
