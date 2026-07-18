import type { ReactNode } from "react";

import { ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useContact,
  useCustomAttributeDefinitions,
} from "@/features/customer-profile/api";

import { AssignmentSection } from "./sections/AssignmentSection";
import { ConversationHistorySection } from "./sections/ConversationHistorySection";
import { CustomAttributesSection } from "./sections/CustomAttributesSection";
import { IdentitySection } from "./sections/IdentitySection";
import { NotesSection } from "./sections/NotesSection";
import { TagsSection } from "./sections/TagsSection";
import { TimelineSection } from "./sections/TimelineSection";

interface CustomerProfileProps {
  contactId: string;
  /**
   * Future extension point. Additive CRM modules — lead pipeline, follow-up, conversion, analytics —
   * mount here as composed children, so the profile grows without editing this component or its
   * sections. Rendered full-width below the core sections.
   */
  extensionSlot?: ReactNode;
  /** Optional footer region (e.g. quick actions), rendered last. */
  footer?: ReactNode;
}

/**
 * Reusable customer profile. Fetches the contact via React Query against the generated client and
 * lays the sections out responsively. Conversation-scoped sections (history/notes/assignment) render
 * their structure with honest empty states until their data is available in context. Future CRM
 * surfaces attach via `extensionSlot` rather than modifying this component.
 */
export function CustomerProfile({
  contactId,
  extensionSlot,
  footer,
}: CustomerProfileProps): JSX.Element {
  const contact = useContact(contactId);
  const definitions = useCustomAttributeDefinitions();

  if (contact.isLoading) {
    return (
      <div className="p-6">
        <Spinner label="Loading customer…" />
      </div>
    );
  }

  if (contact.isError || !contact.data) {
    return (
      <div className="p-6">
        <ErrorState
          message={apiErrorMessage(contact.error)}
          onRetry={() => void contact.refetch()}
        />
      </div>
    );
  }

  const person = contact.data;

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      <header className="mb-4">
        <h2 className="text-xl font-bold text-text-primary">
          {person.full_name ?? person.profile_name ?? person.phone_e164}
        </h2>
        <p className="text-sm text-text-secondary">{person.phone_e164}</p>
      </header>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="space-y-4">
          <IdentitySection contact={person} />
          <CustomAttributesSection contact={person} definitions={definitions.data ?? []} />
          <TagsSection contact={person} />
          <AssignmentSection />
        </div>
        <div className="space-y-4">
          <TimelineSection contactId={contactId} />
          <ConversationHistorySection />
          <NotesSection />
        </div>
      </div>

      {/* Extension slot — future CRM modules (pipeline, follow-up, conversion, analytics) mount here. */}
      {extensionSlot ? (
        <section aria-label="Extensions" className="mt-4 space-y-4">
          {extensionSlot}
        </section>
      ) : null}

      {footer ? <footer className="mt-4">{footer}</footer> : null}
    </div>
  );
}
