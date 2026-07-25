import { Megaphone } from "lucide-react";

import { EmptyState, ErrorState, Section, Skeleton } from "@/components/ui";
import { apiErrorMessage, useContactTimeline } from "@/features/customer-profile/api";

/** Campaign-touch history derived from the existing contact event ledger; no campaign API is duplicated. */
export function CampaignHistorySection({ contactId }: { contactId: string }): JSX.Element {
  const timeline = useContactTimeline(contactId);
  const events = (timeline.data ?? []).filter(
    (event) => event.ref_type === "campaign" || event.event_type.toLocaleLowerCase().includes("campaign"),
  );

  return (
    <Section title="Campaign history" description="Campaign touches recorded in this customer's event timeline." icon={<Megaphone aria-hidden className="h-4 w-4" />}>
      {timeline.isLoading ? <div className="space-y-2"><Skeleton className="h-12 w-full" /><Skeleton className="h-12 w-full" /></div> : timeline.isError ? <ErrorState message={apiErrorMessage(timeline.error)} onRetry={() => void timeline.refetch()} /> : events.length === 0 ? <EmptyState compact title="No campaign activity yet" description="Campaign deliveries and responses appear here when the event ledger records them." /> : <ol className="space-y-2">{events.map((event) => <li key={event.id} className="flex items-center justify-between gap-3 rounded-xl border border-border bg-surface-2 px-3 py-2.5"><div><p className="text-sm font-medium capitalize text-text-primary">{event.event_type.replace(/[._]/g," ")}</p><p className="mt-0.5 text-xs text-text-secondary">{event.ref_type ?? "Campaign event"}</p></div><time className="shrink-0 text-xs text-text-disabled">{new Date(event.created_at).toLocaleDateString()}</time></li>)}</ol>}
    </Section>
  );
}
