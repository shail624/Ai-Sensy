import { useState } from "react";
import { Link } from "react-router-dom";

import { Modal } from "@/components/ui";
import { CampaignResultsExportDialog } from "@/features/campaigns/CampaignResultsExportDialog";
import type { Campaign } from "@/features/campaigns/types";
import { api } from "@/lib/api/client";
import { apiErrorMessage, unwrap } from "@/lib/api/errors";

const PRIMARY =
  "inline-flex h-9 items-center rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white hover:bg-[#08393d] disabled:opacity-50";
const FIELD =
  "mt-2 h-[42px] w-full rounded-[8px] bg-[#f0f0f0] px-3 text-sm text-[#4a4a4a] dark:bg-surface-2 dark:text-text-primary";

/** User Report: every customer of one campaign with their delivery status. */
export function UserReportDialog({ campaigns, onClose }: { campaigns: Campaign[]; onClose: () => void }): JSX.Element {
  const [chosen, setChosen] = useState<Campaign | null>(null);
  const [id, setId] = useState(campaigns[0]?.id ?? "");
  if (chosen) return <CampaignResultsExportDialog campaign={chosen} onClose={onClose} />;
  return (
    <Modal title="User Report" onClose={onClose} panelClassName="!max-w-[480px] !rounded-md" contentClassName="!px-6">
      <p className="text-sm text-[#6e6e6e] dark:text-text-secondary">
        Download each customer of a campaign with whether their message was sent, delivered, read or failed.
      </p>
      {campaigns.length === 0 ? (
        <p className="mt-4 text-sm">No campaigns yet.</p>
      ) : (
        <label className="mt-4 block text-sm font-medium text-text-primary">
          Campaign
          <select value={id} onChange={(event) => setId(event.target.value)} className={FIELD}>
            {campaigns.map((campaign) => (
              <option key={campaign.id} value={campaign.id}>{campaign.name}</option>
            ))}
          </select>
        </label>
      )}
      <div className="mt-5 flex justify-end gap-2 border-t border-border pt-3">
        <button type="button" onClick={onClose} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover">Cancel</button>
        <button
          type="button"
          disabled={!id}
          onClick={() => setChosen(campaigns.find((campaign) => campaign.id === id) ?? null)}
          className={PRIMARY}
        >
          Next
        </button>
      </div>
    </Modal>
  );
}

/** Overview Report: totals for every campaign over a period, prepared in Downloads. */
export function OverviewReportDialog({ onClose }: { onClose: () => void }): JSX.Element {
  const [preset, setPreset] = useState<"last_7d" | "last_30d" | "this_month" | "last_month">("last_30d");
  const [state, setState] = useState<"idle" | "busy" | "done">("idle");
  const [error, setError] = useState<string | null>(null);

  async function start(): Promise<void> {
    setState("busy");
    setError(null);
    try {
      unwrap(
        await api.POST("/api/v1/analytics/reports/export", {
          body: { report: "campaigns", format: "csv", filters: { preset, granularity: "day" } },
        }),
      );
      setState("done");
    } catch (caught) {
      setError(apiErrorMessage(caught));
      setState("idle");
    }
  }

  return (
    <Modal title="Overview Report" onClose={onClose} panelClassName="!max-w-[480px] !rounded-md" contentClassName="!px-6">
      <p className="text-sm text-[#6e6e6e] dark:text-text-secondary">
        Campaign totals per day — targeted, sent, delivered, read, failed and skipped — as a CSV.
      </p>
      <label className="mt-4 block text-sm font-medium text-text-primary">
        Period
        <select value={preset} onChange={(event) => setPreset(event.target.value as typeof preset)} className={FIELD}>
          <option value="last_7d">Last 7 days</option>
          <option value="last_30d">Last 30 days</option>
          <option value="this_month">This month</option>
          <option value="last_month">Last month</option>
        </select>
      </label>
      {state === "done" ? (
        <p role="status" className="mt-4 rounded-md bg-success-soft px-3 py-2 text-sm text-success-on-soft">
          Your report is being prepared. Find it in <Link to="/downloads?category=campaigns" className="font-medium underline">Downloads</Link> in a minute.
        </p>
      ) : null}
      {error ? <p role="alert" className="mt-4 rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-on-soft">{error}</p> : null}
      <div className="mt-5 flex justify-end gap-2 border-t border-border pt-3">
        <button type="button" onClick={onClose} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover">
          {state === "done" ? "Close" : "Cancel"}
        </button>
        {state !== "done" ? (
          <button type="button" disabled={state === "busy"} onClick={() => void start()} className={PRIMARY}>
            {state === "busy" ? "Starting…" : "Download"}
          </button>
        ) : null}
      </div>
    </Modal>
  );
}
