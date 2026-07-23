import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useCampaignRecipients } from "@/features/campaigns/api";
import { RecipientStatusChip } from "@/features/campaigns/CampaignBadges";
import { formatCount, formatDateTime } from "@/features/campaigns/format";
import { RECIPIENT_STATUS_LABELS, RECIPIENT_STATUSES } from "@/features/campaigns/types";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

/**
 * The per-recipient ledger (FR-CAM-10) — who was targeted, what happened to them, and why a
 * failure failed.
 *
 * The endpoint pages at a fixed 50 and accepts `cursor`/`status`, but reads both off the raw query
 * string rather than declaring them, so neither is reachable through the generated client. This
 * renders the one page the contract exposes, filters within it, and says plainly when there is more
 * — rather than drawing pagination controls that cannot advance.
 */
export function CampaignRecipients({ campaignId }: { campaignId: string }): JSX.Element {
  const [status, setStatus] = useState("");
  const recipients = useCampaignRecipients(campaignId);

  const rows = useMemo(() => {
    const data = recipients.data?.data ?? [];
    return status ? data.filter((row) => row.status === status) : data;
  }, [recipients.data, status]);

  return (
    <Section
      title="Recipients"
      action={
        <select
          aria-label="Filter recipients by status"
          value={status}
          onChange={(event) => setStatus(event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All statuses</option>
          {RECIPIENT_STATUSES.map((value) => (
            <option key={value} value={value}>
              {RECIPIENT_STATUS_LABELS[value]}
            </option>
          ))}
        </select>
      }
    >
      {recipients.isLoading ? (
        <Spinner label="Loading recipients…" />
      ) : recipients.isError ? (
        <ErrorState
          message={apiErrorMessage(recipients.error)}
          onRetry={() => void recipients.refetch()}
        />
      ) : (recipients.data?.data ?? []).length === 0 ? (
        <EmptyState
          title="No recipients yet"
          description="The audience roster is built when the campaign is created or edited."
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="None with that status"
          description="No recipient on this page matches the selected status."
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Contact</th>
                  <th scope="col" className="px-3 py-2">Status</th>
                  <th scope="col" className="hidden px-3 py-2 sm:table-cell">Error</th>
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Added</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, index) => (
                  <tr
                    key={`${row.contact_id ?? "unknown"}-${index}`}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-3 py-2">
                      {row.contact_id ? (
                        <Link
                          to={`/contacts/${row.contact_id}`}
                          className="text-text-primary hover:text-accent"
                        >
                          {row.wa_id ?? row.contact_id}
                        </Link>
                      ) : (
                        <span className="text-text-secondary">{row.wa_id ?? "—"}</span>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <RecipientStatusChip value={row.status} />
                    </td>
                    <td className="hidden px-3 py-2 sm:table-cell">
                      {row.error_code ? (
                        <span className="font-mono text-xs text-danger">{row.error_code}</span>
                      ) : (
                        <span className="text-text-disabled">—</span>
                      )}
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                      {formatDateTime(row.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-2 text-xs text-text-disabled">
            Showing {formatCount(rows.length)} of the first page.
            {recipients.data?.has_more
              ? " More recipients exist — paging beyond the first page is not available from this screen yet."
              : ""}
          </p>
        </>
      )}
    </Section>
  );
}
