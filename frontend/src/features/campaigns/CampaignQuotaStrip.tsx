import { useQuery } from "@tanstack/react-query";
import { Info } from "lucide-react";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

const QUALITY: Record<string, { label: string; pill: string }> = {
  GREEN: { label: "High", pill: "bg-[#22c55e] text-white" },
  YELLOW: { label: "Medium", pill: "bg-[#f59e0b] text-white" },
  RED: { label: "Low", pill: "bg-[#ef4444] text-white" },
};

const TIER_NUMBER: Record<string, string> = {
  TIER_50: "Tier 0 (50/24 Hours)",
  TIER_250: "Tier 0 (250/24 Hours)",
  TIER_1K: "Tier 1 (1K/24 Hours)",
  TIER_10K: "Tier 2 (10K/24 Hours)",
  TIER_100K: "Tier 3 (100K/24 Hours)",
  TIER_UNLIMITED: "Unlimited",
};

export function useMessagingQuota() {
  return useQuery({
    queryKey: ["campaigns", "messaging-quota"],
    queryFn: async () => unwrap(await api.GET("/api/v1/campaigns/messaging-quota")),
    refetchInterval: 60_000,
  });
}

function Hint({ text }: { text: string }): JSX.Element {
  return (
    <span title={text} className="inline-flex text-[#9e9e9e]">
      <Info aria-hidden className="h-4 w-4" />
      <span className="sr-only">{text}</span>
    </span>
  );
}

/**
 * The reference strip above the campaign list: the sending number's quality, its messaging tier
 * and how many new customers it can still reach today. Remaining quota is counted from this
 * platform's own template sends in the last 24 hours (Meta does not report it).
 */
export function CampaignQuotaStrip({ action }: { action?: JSX.Element | null }): JSX.Element {
  const quota = useMessagingQuota();
  const number = quota.data?.[0];
  const quality = QUALITY[(number?.quality_rating ?? "").toUpperCase()];
  const tier = number?.messaging_tier ? TIER_NUMBER[number.messaging_tier.toUpperCase()] ?? number.messaging_tier : null;

  return (
    <div className="flex flex-wrap items-center gap-x-8 gap-y-3 rounded-[8px] bg-surface px-5 py-4">
      <div className="flex items-center gap-3">
        <span className="text-sm leading-tight text-[#6e6e6e] dark:text-text-secondary">Quality<br />Rating</span>
        <Hint text="Meta's rating of your number from recent customer feedback. Low quality can pause marketing messages." />
        <span className={`rounded-full px-3 py-1 text-sm font-semibold ${quality?.pill ?? "bg-[#f0f0f0] text-[#6e6e6e]"}`}>
          {quality?.label ?? "Not rated"}
        </span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm leading-tight text-[#6e6e6e] dark:text-text-secondary">Template Messaging<br />Tier</span>
        <Hint text="How many different customers Meta lets this number message first in 24 hours." />
        <span className="text-base font-medium text-black dark:text-text-primary">{tier ?? "Not reported yet"}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className="text-sm leading-tight text-[#6e6e6e] dark:text-text-secondary">Remaining<br />Quota</span>
        <Hint text="Estimate: your tier limit minus customers sent a template from this app in the last 24 hours." />
        <span className="text-xl font-medium text-black dark:text-text-primary">
          {number?.remaining != null ? number.remaining.toLocaleString("en-IN") : "—"}
        </span>
      </div>
      {action ? <div className="ml-auto">{action}</div> : null}
    </div>
  );
}
