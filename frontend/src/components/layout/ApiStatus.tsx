import { RefreshCw } from "lucide-react";

import { useAccountSummary } from "@/features/channels/api";
import { API_STATUS_LABELS, type ApiStatus as Status } from "@/features/channels/accountSummary";
import { useHasPermission } from "@/lib/auth";

const TONES: Record<Status, string> = {
  live: "text-[#008000] dark:text-success",
  pending: "text-warning",
  not_connected: "text-danger",
};

/**
 * "WhatsApp Business API Status : LIVE" with its refresh button — shown on every screen's top bar,
 * including Live Chat and the Manage pages that carry their own header.
 */
export function ApiStatus({ className = "" }: { className?: string }): JSX.Element | null {
  const canWaba = useHasPermission("waba:read");
  const account = useAccountSummary(canWaba);
  if (!canWaba) return null;
  const status = account.summary?.status;
  return (
    <div className={`flex shrink-0 items-center gap-1 ${className}`}>
      {status ? (
        <p className="flex items-center whitespace-nowrap text-sm text-[#4a4a4a] dark:text-text-secondary">
          <span className="hidden lg:inline">WhatsApp Business API Status :</span>
          <span className="lg:hidden">API :</span>
          <span className={`px-2 font-medium ${TONES[status]}`}>{API_STATUS_LABELS[status]}</span>
        </p>
      ) : null}
      <button
        type="button"
        aria-label="Refresh account status"
        title="Refresh"
        onClick={() => void account.refetch()}
        className="flex h-[30px] w-[30px] items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        <RefreshCw aria-hidden className={`h-[18px] w-[18px] ${account.isFetching ? "animate-spin [animation-duration:2s]" : ""}`} />
      </button>
    </div>
  );
}
