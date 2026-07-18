import { EmptyState, Section } from "@/components/ui";

/**
 * Conversation history is conversation-scoped. The current OpenAPI contract exposes no
 * `contact` filter on `GET /conversations`, so there is no typed API to list a given contact's
 * conversations yet. This renders the section structure and an explanatory empty state.
 *
 * TODO — When conversation context becomes available (a contact-scoped conversations API, or a
 * conversation supplied to this profile), **reuse the existing Conversation/Inbox module** to render
 * threads here. Do NOT build another conversation viewer — that would duplicate the inbox UI.
 */
export function ConversationHistorySection(): JSX.Element {
  return (
    <Section title="Conversation history">
      <EmptyState
        title="Not available from a contact yet"
        description="Listing a contact's conversations needs a contact-scoped conversations API, which the frozen backend contract does not expose."
      />
    </Section>
  );
}
