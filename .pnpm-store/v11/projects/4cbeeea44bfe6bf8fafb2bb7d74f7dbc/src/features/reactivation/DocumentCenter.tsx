import { FileCheck2, History, Search, ShieldCheck, UsersRound, X } from "lucide-react";
import { useMemo, useState } from "react";

import { Avatar, Badge, Button, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { useContactSearch } from "@/features/contacts/api";
import type { Contact, SegmentRule } from "@/features/contacts/types";
import { DocumentWorkspace } from "@/features/documents";
import { apiErrorMessage } from "@/lib/api/errors";

/** Organization entry point for the real contact-scoped document domain. */
export function DocumentCenter(): JSX.Element {
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Contact | null>(null);
  const rules = useMemo<SegmentRule[]>(() => {
    const value = query.trim();
    if (!value) return [];
    return [{
      group_index: 0,
      field_source: "contact",
      field_key: /\d/.test(value) ? "phone_e164" : "full_name",
      operator: "contains",
      value,
    }];
  }, [query]);
  const contacts = useContactSearch({ rules, cursor: null, limit: 12 });

  if (selected) {
    const name = selected.full_name ?? selected.profile_name ?? selected.phone_e164;
    return (
      <div className="space-y-4">
        <Card className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center" padding={false}>
          <Avatar name={name} />
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-text-primary">{name}</p><p className="mt-0.5 text-xs text-text-secondary">{selected.phone_e164}{selected.email ? ` · ${selected.email}` : ""}</p></div>
          <Badge tone="info">Customer record selected</Badge>
          <Button size="sm" variant="secondary" leftIcon={<X className="h-3.5 w-3.5" />} onClick={() => setSelected(null)}>Change customer</Button>
        </Card>
        <DocumentWorkspace contactId={selected.id} />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 md:grid-cols-3">
        <DocumentCapability icon={ShieldCheck} title="Governed storage" text="Files are scanned, deduplicated, tenant-isolated, and available only through expiring signed links." />
        <DocumentCapability icon={FileCheck2} title="Human verification" text="Reviewers verify, reject with a reason, and handle expiry through explicit controlled transitions." />
        <DocumentCapability icon={History} title="Immutable lineage" text="Every file version and decision remains attributable in document history and Customer 360." />
      </div>

      <Card className="overflow-hidden" padding={false}>
        <div className="grid min-h-[360px] lg:grid-cols-[minmax(0,1fr)_21rem]">
          <div className="p-5 sm:p-6">
            <div className="flex items-start gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent"><UsersRound aria-hidden className="h-5 w-5" /></span><div><h2 className="text-base font-semibold text-text-primary">Choose a customer</h2><p className="mt-1 text-sm text-text-secondary">Documents are deliberately customer-scoped. Select a record to open its secure workspace.</p></div></div>
            <label className="mt-5 flex h-11 items-center gap-2 rounded-xl border border-border bg-surface px-3 shadow-sm focus-within:border-accent focus-within:ring-2 focus-within:ring-accent-soft">
              <Search aria-hidden className="h-4 w-4 text-text-disabled" />
              <span className="sr-only">Search customers</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by customer name or mobile number" className="w-full bg-transparent text-sm text-text-primary outline-none placeholder:text-text-disabled" autoFocus />
            </label>

            {contacts.isLoading ? <div className="mt-4 space-y-2"><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /></div> : null}
            {contacts.isError ? <div className="mt-4"><ErrorState message={apiErrorMessage(contacts.error)} onRetry={() => void contacts.refetch()} /></div> : null}
            {contacts.data?.data.length === 0 ? <div className="mt-5"><EmptyState compact title="No customers found" description="Try a different name or mobile number." /></div> : null}
            {contacts.data?.data.length ? (
              <div className="mt-4 divide-y divide-border overflow-hidden rounded-xl border border-border">
                {contacts.data.data.map((contact) => {
                  const name = contact.full_name ?? contact.profile_name ?? contact.phone_e164;
                  return <button key={contact.id} type="button" onClick={() => setSelected(contact)} className="flex w-full items-center gap-3 bg-surface p-3 text-left transition hover:bg-hover"><Avatar name={name} size="sm" /><span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold text-text-primary">{name}</span><span className="mt-0.5 block truncate text-xs text-text-secondary">{contact.phone_e164}{contact.email ? ` · ${contact.email}` : ""}</span></span><Badge tone={contact.is_active_on_wa ? "success" : "neutral"}>{contact.is_active_on_wa ? "WhatsApp active" : "CRM"}</Badge></button>;
                })}
              </div>
            ) : null}
          </div>
          <div className="flex items-center justify-center border-t border-border bg-[radial-gradient(circle_at_top,var(--color-accent-soft),var(--color-bg-surface-2))] p-6 lg:border-l lg:border-t-0">
            <EmptyState icon={<ShieldCheck className="h-7 w-7" />} title="One trusted customer record" description="Verification status, file lineage, reviewer actions, and expiry stay attached to the correct customer." />
          </div>
        </div>
      </Card>
    </div>
  );
}

function DocumentCapability({ icon: Icon, title, text }: { icon: typeof ShieldCheck; title: string; text: string }): JSX.Element {
  return <Card className="p-4" padding={false}><div className="flex items-start justify-between gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent"><Icon aria-hidden className="h-4 w-4" /></span><Badge tone="success" dot>Connected</Badge></div><h2 className="mt-3 text-sm font-semibold text-text-primary">{title}</h2><p className="mt-1 text-xs leading-relaxed text-text-secondary">{text}</p></Card>;
}
