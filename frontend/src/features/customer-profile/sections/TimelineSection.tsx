import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useContactTimeline } from "@/features/customer-profile/api";
import type { ContactEvent } from "@/features/customer-profile/types";

function label(event: ContactEvent): string {
  return event.event_type.replace(/[._]/g, " ");
}

/** Activity timeline from `contact_events` (GET /contacts/{id}/timeline). */
export function TimelineSection({ contactId }: { contactId: string }): JSX.Element {
  const timeline = useContactTimeline(contactId);
  const events = timeline.data ?? [];

  return (
    <Section title="Timeline & activity">
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
            <li key={event.id} className="flex items-start gap-2 text-sm">
              <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-accent" />
              <div>
                <p className="capitalize text-text-primary">{label(event)}</p>
                <p className="text-xs text-text-secondary">
                  {new Date(event.created_at).toLocaleString()}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Section>
  );
}
