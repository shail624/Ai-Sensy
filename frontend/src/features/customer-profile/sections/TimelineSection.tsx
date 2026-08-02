import { ExternalLink, History, ShieldCheck } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useContactTimeline } from "@/features/customer-profile/api";
import type { ContactEvent } from "@/features/customer-profile/types";

function label(event: ContactEvent): string {
  return event.event_type.replace(/[._]/g, " ");
}

/** Activity timeline from `contact_events` (GET /contacts/{id}/timeline). */
export function TimelineSection({ contactId, mode = "timeline" }: { contactId: string; mode?: "timeline" | "audit" }): JSX.Element {
  const navigate = useNavigate();
  const timeline = useContactTimeline(contactId);
  const events = timeline.data ?? [];
  const auditMode = mode === "audit";

  return (
    <Section
      title={auditMode ? "Customer audit evidence" : "Customer Timeline"}
      description={auditMode ? "Attributed workflow evidence projected into the customer ledger; organization-wide audit remains the administrative authority." : "One chronological stream across contact, messaging, campaign, task and Vi workflows."}
      icon={auditMode ? <ShieldCheck aria-hidden className="h-4 w-4" /> : <History aria-hidden className="h-4 w-4" />}
      action={auditMode ? <Button variant="secondary" leftIcon={<ExternalLink aria-hidden className="h-4 w-4" />} onClick={() => navigate("/admin/audit")}>Open audit trail</Button> : null}
    >
      {timeline.isLoading ? (
        <Spinner />
      ) : timeline.isError ? (
        <ErrorState
          message={apiErrorMessage(timeline.error)}
          onRetry={() => void timeline.refetch()}
        />
      ) : events.length === 0 ? (
        <EmptyState
          title="No activity yet"
          description="Contact events, messages and campaign activity appear here."
        />
      ) : (
        <ol className="space-y-2">
          {events.map((event) => (
            <li key={event.id} className="flex items-start gap-3 rounded-xl border border-border bg-surface-2 px-3 py-2.5 text-sm">
              <span aria-hidden className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-accent" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2"><p className="capitalize font-medium text-text-primary">{label(event)}</p>{event.ref_type ? <Badge>{event.ref_type.replace(/_/g, " ")}</Badge> : null}</div>
                <time className="mt-1 block text-xs text-text-secondary">{new Date(event.created_at).toLocaleString()}</time>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Section>
  );
}
