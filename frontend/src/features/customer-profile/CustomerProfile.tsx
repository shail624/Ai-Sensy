import {
  CalendarDays,
  CircleUserRound,
  FileText,
  History,
  ListChecks,
  MessageCircle,
  Megaphone,
  ShieldCheck,
  Tags,
} from "lucide-react";
import { useState, type KeyboardEvent, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import {
  Avatar,
  Badge,
  Button,
  DefinitionRow,
  EmptyState,
  ErrorState,
  Section,
  Skeleton,
} from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import { apiErrorMessage, useContact, useCustomAttributeDefinitions } from "@/features/customer-profile/api";
import { useHasPermission } from "@/lib/auth";

import { CampaignHistorySection } from "./sections/CampaignHistorySection";
import { ConversationHistorySection } from "./sections/ConversationHistorySection";
import { CustomAttributesSection } from "./sections/CustomAttributesSection";
import { DocumentsSection } from "./sections/DocumentsSection";
import { IdentitySection } from "./sections/IdentitySection";
import { ReactivationSection } from "./sections/ReactivationSection";
import { TagsSection } from "./sections/TagsSection";
import { TimelineSection } from "./sections/TimelineSection";

const OPT_IN: Record<string, { tone: BadgeTone; label: string }> = {
  opted_in: { tone: "success", label: "Opted in" },
  opted_out: { tone: "danger", label: "Opted out" },
  pending: { tone: "warning", label: "Pending" },
  unknown: { tone: "neutral", label: "Unknown" },
};

const TABS = [
  { key: "overview", label: "Overview", icon: CircleUserRound },
  { key: "operations", label: "Vi operations", icon: ListChecks },
  { key: "conversations", label: "Conversations", icon: MessageCircle },
  { key: "timeline", label: "Timeline", icon: History },
  { key: "tasks", label: "Tasks", icon: CalendarDays },
  { key: "documents", label: "Documents", icon: FileText },
  { key: "campaigns", label: "Campaigns", icon: Megaphone },
  { key: "audit", label: "Audit", icon: ShieldCheck },
] as const;
type ProfileTab = (typeof TABS)[number]["key"];

interface CustomerProfileProps {
  contactId: string;
  extensionSlot?: ReactNode;
}

function tabKeydown(event: KeyboardEvent<HTMLButtonElement>, index: number): void {
  const buttons = Array.from(
    event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? [],
  );
  if (!buttons.length) return;
  let next = index;
  if (event.key === "ArrowRight") next = (index + 1) % buttons.length;
  else if (event.key === "ArrowLeft") next = (index - 1 + buttons.length) % buttons.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = buttons.length - 1;
  else return;
  event.preventDefault();
  buttons[next]?.focus();
  buttons[next]?.click();
}

export function CustomerProfile({ contactId, extensionSlot }: CustomerProfileProps): JSX.Element {
  const navigate = useNavigate();
  const [tab, setTab] = useState<ProfileTab>("overview");
  const contact = useContact(contactId);
  const definitions = useCustomAttributeDefinitions();
  const canInbox = useHasPermission("inbox:read");
  const canCampaign = useHasPermission("campaigns:write");
  const canAudit = useHasPermission("audit:read");

  if (contact.isLoading) {
    return <PageContainer><Skeleton className="h-5 w-48" /><div className="mt-5 rounded-2xl border border-border bg-surface p-6"><Skeleton className="h-16 w-full" /><Skeleton className="mt-6 h-72 w-full" /></div></PageContainer>;
  }

  if (contact.isError || !contact.data) {
    return <PageContainer><Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Contacts", to: "/contacts" }, { label: "Customer" }]} /><ErrorState message={apiErrorMessage(contact.error)} onRetry={() => void contact.refetch()} /></PageContainer>;
  }

  const person = contact.data;
  const name = person.full_name ?? person.profile_name ?? person.phone_e164;
  const status = OPT_IN[person.opt_in_status] ?? { tone: "neutral" as const, label: person.opt_in_status };

  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Contacts", to: "/contacts" }, { label: name }]} />
      <PageHeader
        eyebrow="Customer 360"
        title={name}
        description={`${person.phone_e164}${person.email ? ` · ${person.email}` : ""}`}
        meta={<><Badge tone={status.tone} dot>{status.label}</Badge><Badge tone={person.is_active_on_wa ? "success" : "neutral"}>{person.is_active_on_wa ? "WhatsApp active" : "WhatsApp status unknown"}</Badge></>}
        actions={<>{canInbox ? <Button variant="secondary" leftIcon={<MessageCircle className="h-4 w-4" />} onClick={() => navigate(`/inbox?q=${encodeURIComponent(person.phone_e164)}`)}>Open inbox</Button> : null}{canCampaign ? <Button leftIcon={<Megaphone className="h-4 w-4" />} onClick={() => navigate("/campaigns/new", { state: { contactIds: [person.id] } })}>Add to campaign</Button> : null}</>}
      />

      <section aria-label="Customer identity summary" className="mb-5 overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        <div className="relative flex flex-col gap-4 overflow-hidden p-4 sm:flex-row sm:items-center sm:p-5">
          <div aria-hidden className="absolute inset-y-0 right-0 w-1/3 bg-gradient-to-l from-accent-soft/70 to-transparent" />
          <Avatar name={name} size="lg" />
          <div className="relative min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2"><p className="text-sm font-semibold text-text-primary">Single customer identity</p><Badge tone="accent"><Tags aria-hidden className="h-3 w-3" />{person.tags.length} {person.tags.length === 1 ? "tag" : "tags"}</Badge></div>
            <p className="mt-1 text-xs text-text-secondary">Persisted since {new Date(person.created_at).toLocaleDateString()} · last profile update {new Date(person.updated_at).toLocaleDateString()}</p>
          </div>
          <div className="relative grid grid-cols-2 gap-2 text-xs sm:min-w-64">
            <div className="rounded-xl border border-border bg-surface/80 px-3 py-2"><p className="text-text-disabled">Source</p><p className="mt-1 truncate font-semibold text-text-primary">{person.source || "Not recorded"}</p></div>
            <div className="rounded-xl border border-border bg-surface/80 px-3 py-2"><p className="text-text-disabled">Last contact</p><p className="mt-1 truncate font-semibold text-text-primary">{person.last_contacted_at ? new Date(person.last_contacted_at).toLocaleDateString() : "No event"}</p></div>
          </div>
        </div>
        <nav aria-label="Customer workspace sections" role="tablist" className="flex gap-1 overflow-x-auto border-t border-border px-2 py-2">
          {TABS.map(({ key, label, icon: Icon }, index) => (
            <button
              key={key}
              id={`customer-tab-${key}`}
              type="button"
              role="tab"
              aria-selected={tab === key}
              aria-controls={`customer-panel-${key}`}
              tabIndex={tab === key ? 0 : -1}
              onClick={() => setTab(key)}
              onKeyDown={(event) => tabKeydown(event, index)}
              className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${tab === key ? "bg-accent text-accent-fg shadow-sm" : "text-text-secondary hover:bg-hover hover:text-text-primary"}`}
            ><Icon aria-hidden className="h-3.5 w-3.5" />{label}</button>
          ))}
        </nav>
      </section>

      <div id={`customer-panel-${tab}`} role="tabpanel" aria-labelledby={`customer-tab-${tab}`} tabIndex={0} className="focus-visible:outline-none">
        {tab === "overview" ? <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.15fr)_minmax(20rem,.85fr)]"><div className="space-y-4"><IdentitySection contact={person} /><CustomAttributesSection contact={person} definitions={definitions.data ?? []} /></div><div className="space-y-4"><TagsSection contact={person} /><Section title="Engagement facts" description="Directly persisted contact timestamps; no synthetic score."><dl><DefinitionRow label="Last inbound">{person.last_inbound_at ? new Date(person.last_inbound_at).toLocaleString() : "No inbound message"}</DefinitionRow><DefinitionRow label="Last outbound">{person.last_outbound_at ? new Date(person.last_outbound_at).toLocaleString() : "No outbound message"}</DefinitionRow><DefinitionRow label="WhatsApp identity">{person.wa_id}</DefinitionRow><DefinitionRow label="Record version">{person.row_version}</DefinitionRow></dl></Section></div></div> : null}
        {tab === "operations" ? <ReactivationSection contact={person} /> : null}
        {tab === "conversations" ? <ConversationHistorySection contactId={contactId} /> : null}
        {tab === "timeline" ? <TimelineSection contactId={contactId} /> : null}
        {tab === "tasks" ? extensionSlot ?? <EmptyState title="No task workspace connected" /> : null}
        {tab === "documents" ? <DocumentsSection contactId={contactId} /> : null}
        {tab === "campaigns" ? <CampaignHistorySection contactId={contactId} /> : null}
        {tab === "audit" ? canAudit ? <TimelineSection contactId={contactId} mode="audit" /> : <Section title="Audit"><EmptyState compact title="Audit access is restricted" description="Your role cannot view organization audit evidence." /></Section> : null}
      </div>

    </PageContainer>
  );
}
