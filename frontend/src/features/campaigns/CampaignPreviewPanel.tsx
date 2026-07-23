import { useState } from "react";

import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useCampaignEstimate,
  useCampaignPreview,
  useHasPermission,
} from "@/features/campaigns/api";
import { formatCount, formatMoney } from "@/features/campaigns/format";

interface SampleRender {
  contact_id?: unknown;
  wa_id?: unknown;
  rendered?: { header?: unknown; body?: unknown; footer?: unknown };
}

function text(value: unknown): string {
  return typeof value === "string" ? value : "";
}

/**
 * What will actually be sent (FR-CAM-02) and what it will cost (FR-CAM-11).
 *
 * Both read the **materialized roster**, so this shows the campaign as stored rather than
 * re-resolving the audience — the preview must answer "what goes out", not "what would match now".
 * The cost estimate is opt-in: it caches its quote on the campaign row and answers 422 when the
 * rate card is not configured, so it runs when the operator asks for a price.
 */
export function CampaignPreviewPanel({ campaignId }: { campaignId: string }): JSX.Element {
  const [wantsCost, setWantsCost] = useState(false);
  const canSeeCost = useHasPermission("campaigns:read");

  const preview = useCampaignPreview(campaignId, true);
  const estimate = useCampaignEstimate(campaignId, wantsCost && canSeeCost);

  const samples = (preview.data?.samples ?? []) as SampleRender[];

  return (
    <div className="space-y-4">
      <Section title="Audience preview">
        {preview.isLoading ? (
          <Spinner label="Resolving audience…" />
        ) : preview.isError ? (
          <ErrorState
            message={apiErrorMessage(preview.error)}
            onRetry={() => void preview.refetch()}
          />
        ) : (
          <>
            <div className="flex flex-wrap gap-6">
              <div>
                <p className="text-xs font-medium text-text-secondary">Will receive</p>
                <p className="mt-1 text-2xl font-semibold text-text-primary">
                  {formatCount(preview.data?.total)}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-text-secondary">Excluded (opted out)</p>
                <p className="mt-1 text-2xl font-semibold text-text-primary">
                  {formatCount(preview.data?.excluded_opted_out)}
                </p>
                <p className="mt-0.5 text-xs text-text-disabled">
                  Removed automatically — they cannot be messaged.
                </p>
              </div>
            </div>

            {samples.length === 0 ? (
              <div className="mt-3">
                <EmptyState
                  title="No recipients"
                  description="This audience resolved to nobody. Check the segment, tags or contact list."
                />
              </div>
            ) : (
              <ul className="mt-4 space-y-2">
                {samples.map((sample, index) => (
                  <li
                    key={text(sample.contact_id) || index}
                    className="rounded-md border border-border bg-surface-2 p-3"
                  >
                    <p className="text-xs text-text-secondary">{text(sample.wa_id) || "—"}</p>
                    {text(sample.rendered?.header) ? (
                      <p className="mt-1 text-sm font-semibold text-text-primary">
                        {text(sample.rendered?.header)}
                      </p>
                    ) : null}
                    <p className="mt-1 whitespace-pre-wrap text-sm text-text-primary">
                      {text(sample.rendered?.body)}
                    </p>
                    {text(sample.rendered?.footer) ? (
                      <p className="mt-1 text-xs text-text-disabled">
                        {text(sample.rendered?.footer)}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </Section>

      <Section
        title="Cost estimate"
        action={
          !wantsCost ? (
            <button
              type="button"
              onClick={() => setWantsCost(true)}
              className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
            >
              Estimate cost
            </button>
          ) : null
        }
      >
        {!wantsCost ? (
          <EmptyState
            title="Not estimated yet"
            description="Prices this campaign's roster against the rate card."
          />
        ) : estimate.isLoading ? (
          <Spinner label="Pricing recipients…" />
        ) : estimate.isError ? (
          <ErrorState message={apiErrorMessage(estimate.error)} />
        ) : estimate.data ? (
          <>
            <div className="flex flex-wrap items-baseline gap-2">
              <p className="text-2xl font-semibold text-text-primary">
                {formatMoney(estimate.data.estimated_total, estimate.data.currency)}
              </p>
              <p className="text-xs text-text-secondary">
                for {formatCount(estimate.data.recipients)} recipients
              </p>
            </div>

            {estimate.data.breakdown.length > 0 ? (
              <div className="mt-3 overflow-x-auto rounded-md border border-border">
                <table className="w-full text-left text-sm">
                  <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                    <tr>
                      <th scope="col" className="px-3 py-2">Country</th>
                      <th scope="col" className="px-3 py-2">Category</th>
                      <th scope="col" className="px-3 py-2 text-right">Recipients</th>
                      <th scope="col" className="px-3 py-2 text-right">Unit</th>
                      <th scope="col" className="px-3 py-2 text-right">Subtotal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {estimate.data.breakdown.map((row) => (
                      <tr
                        key={`${row.country}-${row.category}`}
                        className="border-b border-border last:border-0"
                      >
                        <td className="px-3 py-2 text-text-primary">{row.country}</td>
                        <td className="px-3 py-2 text-text-secondary">{row.category}</td>
                        <td className="px-3 py-2 text-right text-text-secondary">
                          {formatCount(row.count)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-text-secondary">
                          {formatMoney(row.unit)}
                        </td>
                        <td className="px-3 py-2 text-right font-mono text-text-primary">
                          {formatMoney(row.subtotal)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}

            {estimate.data.unresolved.count > 0 ? (
              <p className="mt-3 text-xs text-warning">
                {formatCount(estimate.data.unresolved.count)} recipients could not be priced
                ({estimate.data.unresolved.reason}); they are excluded from the total above, not
                from the send.
              </p>
            ) : null}

            {estimate.data.notes.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {estimate.data.notes.map((note) => (
                  <li key={note} className="text-xs text-text-disabled">
                    {note}
                  </li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}
      </Section>
    </div>
  );
}
