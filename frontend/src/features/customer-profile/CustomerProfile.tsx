import { Activity, MessageCircle, Megaphone, Sparkles } from "lucide-react";
import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Avatar, Badge, Button, EmptyState, ErrorState, Section, Skeleton } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import { apiErrorMessage, useContact, useCustomAttributeDefinitions } from "@/features/customer-profile/api";
import { useHasPermission } from "@/lib/auth";

import { AssignmentSection } from "./sections/AssignmentSection";
import { CampaignHistorySection } from "./sections/CampaignHistorySection";
import { ConversationHistorySection } from "./sections/ConversationHistorySection";
import { CustomAttributesSection } from "./sections/CustomAttributesSection";
import { DocumentsSection } from "./sections/DocumentsSection";
import { IdentitySection } from "./sections/IdentitySection";
import { NotesSection } from "./sections/NotesSection";
import { ReactivationSection } from "./sections/ReactivationSection";
import { TagsSection } from "./sections/TagsSection";
import { TimelineSection } from "./sections/TimelineSection";

const OPT_IN: Record<string, { tone: BadgeTone; label: string }> = {
  opted_in: { tone: "success", label: "Opted in" },
  opted_out: { tone: "danger", label: "Opted out" },
  pending: { tone: "warning", label: "Pending" },
  unknown: { tone: "neutral", label: "Unknown" },
};

const TABS = ["overview", "timeline", "conversation", "campaign-history", "documents", "kyc", "sim", "tasks", "internal-notes", "audit", "activity", "ai"] as const;
type ProfileTab = (typeof TABS)[number];
const TAB_LABELS: Record<ProfileTab, string> = { overview: "Overview", timeline: "Timeline", conversation: "Conversation", "campaign-history": "Campaign History", documents: "Documents", kyc: "KYC", sim: "SIM", tasks: "Tasks", "internal-notes": "Internal Notes", audit: "Audit", activity: "Activity", ai: "AI Assistant" };

interface CustomerProfileProps {
  contactId: string;
  extensionSlot?: ReactNode;
  footer?: ReactNode;
}

export function CustomerProfile({ contactId, extensionSlot, footer }: CustomerProfileProps): JSX.Element {
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
      <PageHeader eyebrow="Customer 360" title={name} description={`${person.phone_e164}${person.email ? ` · ${person.email}` : ""}`} meta={<><Badge tone={status.tone} dot>{status.label}</Badge><Badge tone={person.is_active_on_wa ? "success" : "neutral"}>{person.is_active_on_wa ? "WhatsApp active" : "WhatsApp status unknown"}</Badge></>} actions={<>{canInbox ? <Button variant="secondary" leftIcon={<MessageCircle className="h-4 w-4" />} onClick={() => navigate(`/inbox?q=${encodeURIComponent(person.phone_e164)}`)}>Open inbox</Button> : null}{canCampaign ? <Button leftIcon={<Megaphone className="h-4 w-4" />} onClick={() => navigate("/campaigns/new", { state: { contactIds: [person.id] } })}>Add to campaign</Button> : null}</>} />

      <div className="mb-6 overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-center sm:p-5">
          <Avatar name={name} size="lg" />
          <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-text-primary">Customer profile</p><p className="mt-1 text-xs text-text-secondary">Created {new Date(person.created_at).toLocaleDateString()} · updated {new Date(person.updated_at).toLocaleDateString()}</p></div>
          <span className="inline-flex items-center gap-1.5 rounded-xl bg-accent-soft px-3 py-2 text-xs font-medium text-accent"><Sparkles aria-hidden className="h-3.5 w-3.5" />Complete customer context</span>
        </div>
        <nav aria-label="Customer profile sections" role="tablist" className="flex gap-1 overflow-x-auto border-t border-border px-2 py-2">
          {TABS.map((key) => <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => setTab(key)} className={`min-h-10 shrink-0 rounded-xl px-3 text-sm font-medium transition-colors ${tab === key ? "bg-accent text-accent-fg shadow-sm" : "text-text-secondary hover:bg-hover hover:text-text-primary"}`}>{TAB_LABELS[key]}</button>)}
        </nav>
      </div>

      {tab === "overview" ? <div className="grid grid-cols-1 gap-4 lg:grid-cols-2"><div className="space-y-4"><IdentitySection contact={person} /><CustomAttributesSection contact={person} definitions={definitions.data ?? []} /></div><div className="space-y-4"><TagsSection contact={person} /><AssignmentSection />{extensionSlot ? <section aria-label="Customer work" className="space-y-4">{extensionSlot}</section> : null}</div></div> : null}
      {tab === "timeline" ? <TimelineSection contactId={contactId} /> : null}
      {tab === "conversation" ? <ConversationHistorySection /> : null}
      {tab === "campaign-history" ? <CampaignHistorySection contactId={contactId} /> : null}
      {tab === "documents" ? <DocumentsSection contactId={contactId} /> : null}
      {tab === "kyc" ? <ReactivationSection contact={person} focus="kyc" /> : null}
      {tab === "sim" ? <ReactivationSection contact={person} focus="sim" /> : null}
      {tab === "tasks" ? extensionSlot ?? <EmptyState title="No task workspace connected" /> : null}
      {tab === "internal-notes" ? <NotesSection /> : null}
      {tab === "audit" ? <Section title="Audit" description="Immutable organization audit remains the authority for administrative and workflow changes."><EmptyState compact title="Contact-specific audit filter unavailable" description="The current audit API does not expose a contact-scoped contract, so unrelated entries are not embedded here." action={canAudit ? <Button variant="secondary" onClick={() => navigate("/admin/audit")}>Open audit trail</Button> : undefined} /></Section> : null}
      {tab === "activity" ? <Section title="Activity" description="Customer, task, campaign, and CRM events share the append-only timeline instead of a duplicate activity ledger."><div className="flex flex-col items-start gap-3 rounded-xl border border-border bg-surface-2 p-4"><div className="flex items-center gap-2 text-sm font-semibold text-text-primary"><Activity aria-hidden className="h-4 w-4 text-accent" />One chronological source</div><p className="text-sm leading-relaxed text-text-secondary">Use Timeline for the complete verified history. Task completion can append outcomes into that same event stream.</p><Button variant="secondary" onClick={() => setTab("timeline")}>Open timeline</Button></div></Section> : null}
      {tab === "ai" ? footer ?? <Section title="AI Assistant"><EmptyState compact title="AI provider not connected" /></Section> : null}
    </PageContainer>
  );
}
