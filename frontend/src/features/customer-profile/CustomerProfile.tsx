import type { ReactNode } from "react";

import { Avatar, Badge, ErrorState, Spinner } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import {
  apiErrorMessage,
  useContact,
  useCustomAttributeDefinitions,
} from "@/features/customer-profile/api";

/** Opt-in vocabulary → a status pill; anything unknown renders neutrally rather than guessing. */
const OPT_IN: Record<string, { tone: BadgeTone; label: string }> = {
  opted_in: { tone: "success", label: "Opted in" },
  opted_out: { tone: "danger", label: "Opted out" },
  pending: { tone: "warning", label: "Pending" },
  unknown: { tone: "neutral", label: "Unknown" },
};

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
  const name = person.full_name ?? person.profile_name ?? person.phone_e164;
  const status = OPT_IN[person.opt_in_status] ?? { tone: "neutral" as const, label: person.opt_in_status };

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      {/* Identity header (Doc 05 B3.2): who this is, and their standing, before any detail. */}
      <header className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-surface p-4 shadow-sm sm:gap-4 sm:p-5">
        <Avatar name={name} size="lg" />
        <div className="min-w-0 flex-1">
          <h2 className="truncate text-xl font-bold tracking-tight text-text-primary">{name}</h2>
          <p className="truncate text-sm tabular-nums text-text-secondary">{person.phone_e164}</p>
        </div>
        <Badge tone={status.tone} dot>
          {status.label}
        </Badge>
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
