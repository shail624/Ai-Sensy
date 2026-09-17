import { useState } from "react";

import { Badge, type BadgeTone, Button, Card, CardHeader, EmptyState, ErrorState, Input, Skeleton } from "@/components/ui";
import { useStartContactExport } from "@/features/contacts/api";
import { useReachability, useReachabilityCounts } from "@/features/scan/api";
import { VERDICT_HINTS, VERDICT_LABELS, type Verdict } from "@/features/scan/types";
import { apiErrorMessage } from "@/lib/api/errors";

const TONES: Record<Verdict, BadgeTone> = {
  reachable: "success",
  unreachable: "danger",
  unknown: "neutral",
};

const ORDER: Verdict[] = ["reachable", "unreachable", "unknown"];

function day(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleDateString(undefined, { dateStyle: "medium" }) : "—";
}

/**
 * What WhatsApp has told us about our own customers' numbers.
 *
 * This is the compliant answer to "which of these numbers are on WhatsApp". Meta's Cloud API has no
 * lookup, and the tools that claim one drive WhatsApp Web underneath, which this repository's scope
 * excludes. What it does have is delivery evidence from campaigns already sent, which costs nothing
 * extra and is Meta's own word rather than an inference.
 *
 * Both dates are shown beside the verdict on purpose. A delivery in March and a refusal last week
 * are both facts, and the verdict is only the more recent of the two — an operator surprised by a
 * row can see why it says what it says instead of having to trust it.
 */
export function ReachabilityPanel(): JSX.Element {
  const [verdict, setVerdict] = useState<Verdict | "">("");
  const [search, setSearch] = useState("");
  const [exported, setExported] = useState(false);
  // The contacts export addresses people by segment rule, and SCAN-02 made reachability one, so
  // this is scope §13's "Export" through the one export pipeline rather than a second one built
  // beside it. The Download Center, signed links and expiry all come with it unchanged.
  const exporting = useStartContactExport();

  async function startExport(): Promise<void> {
    if (!verdict) return;
    await exporting.mutateAsync({
      format: "csv",
      rules: [
        {
          group_index: 0,
          field_source: "scan",
          field_key: "reachability",
          operator: "eq",
          value: verdict,
        },
      ],
    });
    setExported(true);
  }
  const reachability = useReachability(verdict, search);
  // Asked separately because it costs differently — see `useReachabilityCounts`. The tiles show a
  // dash until it lands rather than holding up the list behind it.
  const tallies = useReachabilityCounts(search);

  const counts = tallies.data;
  const rows = reachability.data?.data ?? [];

  return (
    <Card padding={false} className="overflow-hidden">
      <CardHeader
        className="border-b border-border px-4 py-4 sm:px-5"
        title="WhatsApp reachability"
        description="Read from delivery receipts for campaigns already sent — nothing is sent to produce it, and no number is looked up anywhere."
        action={
          <Button
            variant="secondary"
            size="sm"
            disabled={!verdict || exporting.isPending}
            onClick={() => void startExport()}
          >
            {exporting.isPending ? "Preparing…" : "Export this list"}
          </Button>
        }
      />
      {exported ? (
        <p className="border-b border-border bg-accent-soft px-4 py-2 text-xs text-text-primary sm:px-5">
          Export started. It appears in the Download Center when it is ready.
        </p>
      ) : null}

      <div className="grid gap-2 border-b border-border p-4 sm:grid-cols-3 sm:px-5">
        {ORDER.map((name) => {
          const selected = verdict === name;
          return (
            <button
              key={name}
              type="button"
              aria-pressed={selected}
              onClick={() => {
                setVerdict(selected ? "" : name);
                setExported(false);
              }}
              className={`rounded-xl border p-4 text-left transition-colors ${
                selected ? "border-accent bg-accent-soft" : "border-border bg-surface-subtle hover:border-border-strong"
              }`}
            >
              <p className="text-2xl font-bold text-text-primary">
                {counts ? counts[name].toLocaleString() : "—"}
              </p>
              <p className="text-xs font-semibold text-text-primary">{VERDICT_LABELS[name]}</p>
              <p className="mt-1 text-xs leading-relaxed text-text-secondary">{VERDICT_HINTS[name]}</p>
            </button>
          );
        })}
      </div>

      <div className="border-b border-border p-4 sm:px-5">
        <Input
          aria-label="Search by name or number"
          placeholder="Search by name or number"
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />
      </div>

      <div className="p-4 sm:px-5">
        {reachability.isPending ? (
          <Skeleton className="h-40 rounded-xl" />
        ) : reachability.isError ? (
          <ErrorState
            message={apiErrorMessage(reachability.error)}
            onRetry={() => void reachability.refetch()}
          />
        ) : rows.length === 0 ? (
          <EmptyState
            title="No contacts match"
            description={
              verdict || search
                ? "Clear the filter to see every contact."
                : "Import contacts and send a campaign; reachability appears from the delivery receipts."
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-text-secondary">
                  <th scope="col" className="pb-2 pr-3 font-medium">Customer</th>
                  <th scope="col" className="pb-2 pr-3 font-medium">Number</th>
                  <th scope="col" className="pb-2 pr-3 font-medium">Status</th>
                  <th scope="col" className="pb-2 pr-3 font-medium">Last reached</th>
                  <th scope="col" className="pb-2 font-medium">Last refused</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.contact_id} className="border-b border-border/60 last:border-0">
                    <td className="py-2 pr-3 text-text-primary">{row.full_name ?? "—"}</td>
                    <td className="py-2 pr-3 text-text-secondary">{row.phone_e164 ?? "—"}</td>
                    <td className="py-2 pr-3">
                      <Badge tone={TONES[row.verdict]}>{VERDICT_LABELS[row.verdict]}</Badge>
                    </td>
                    <td className="py-2 pr-3 text-text-secondary">{day(row.last_delivered_at)}</td>
                    <td className="py-2 text-text-secondary">{day(row.last_undeliverable_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {reachability.data?.page.has_more ? (
              <p className="mt-3 text-xs text-text-secondary">
                Showing the first {rows.length}. Narrow with the search or a status above.
              </p>
            ) : null}
          </div>
        )}
      </div>
    </Card>
  );
}
