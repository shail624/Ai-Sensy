import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, Pagination, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useCampaignRecipients } from "@/features/campaigns/api";
import { RecipientStatusChip } from "@/features/campaigns/CampaignBadges";
import { formatCount, formatDateTime } from "@/features/campaigns/format";
import type { RecipientLedgerStatus } from "@/features/campaigns/types";
import { RECIPIENT_STATUS_LABELS, RECIPIENT_STATUSES } from "@/features/campaigns/types";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

function recipientSummary(total: number, status: RecipientLedgerStatus | ""): string {
  const label = status ? (RECIPIENT_STATUS_LABELS[status] ?? status).toLowerCase() : "total";
  return `${formatCount(total)} ${label} ${total === 1 ? "recipient" : "recipients"}`;
}

/**
 * The per-recipient ledger (FR-CAM-10) — who was targeted, what happened to them, and why a
 * failure failed.
 *
 * Filters and cursor navigation run on the server, so a failure operator sees the complete stored
 * roster rather than a filtered fragment of the first page. Only safe failure codes are exposed;
 * provider/internal message identities stay out of this operational surface.
 */
export function CampaignRecipients({ campaignId }: { campaignId: string }): JSX.Element {
  const [status, setStatus] = useState<RecipientLedgerStatus | "">("");
  const [cursors, setCursors] = useState<string[]>([]);
  const recipients = useCampaignRecipients(campaignId, {
    status,
    cursor: cursors.at(-1),
  });
  const rows = recipients.data?.data ?? [];
  const page = recipients.data?.page;

  useEffect(() => setCursors([]), [status]);

  function nextPage(): void {
    const nextCursor = page?.next_cursor;
    if (nextCursor) setCursors((current) => [...current, nextCursor]);
  }

  function previousPage(): void {
    setCursors((current) => current.slice(0, -1));
  }

  return (
    <Section
      title="Recipients"
      action={
        <select
          aria-label="Filter recipients by status"
          value={status}
          onChange={(event) =>
            setStatus(event.target.value as RecipientLedgerStatus | "")
          }
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
      ) : rows.length === 0 ? (
        <EmptyState
          title={status ? "None with that status" : "No recipients yet"}
          description={
            status
              ? "No recipient in the complete campaign roster matches this status."
              : "The audience roster is built when the campaign is created or edited."
          }
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
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Retries</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Updated</th>
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
                          <span className="block">
                            {row.contact_name ?? row.wa_id ?? row.contact_id}
                          </span>
                          {row.contact_name && row.wa_id ? (
                            <span className="block text-xs text-text-secondary">{row.wa_id}</span>
                          ) : null}
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
                      {formatCount(row.retry_count)}
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                      {formatDateTime(
                        row.read_at ??
                          row.delivered_at ??
                          row.failed_at ??
                          row.sent_at ??
                          row.queued_at ??
                          row.created_at,
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Pagination
            label="Campaign recipient pagination"
            hasPrevious={cursors.length > 0}
            hasNext={Boolean(page?.next_cursor)}
            busy={recipients.isFetching}
            onPrevious={previousPage}
            onNext={nextPage}
            summary={
              page?.total != null
                ? recipientSummary(page.total, status)
                : `${formatCount(rows.length)} recipients on this page`
            }
          />
        </>
      )}
    </Section>
  );
}
