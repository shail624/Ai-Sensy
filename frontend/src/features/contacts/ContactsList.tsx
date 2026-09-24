import { Contact as ContactIcon, Megaphone, Plus, Upload } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { ManagePageHeader, MANAGE_PRIMARY_ACTION } from "@/components/layout";
import { Button, EmptyState, ErrorState, Pagination, Skeleton } from "@/components/ui";
import { SALE_STATUS_OPTIONS } from "@/features/inbox/saleStatus";
import { QuickGuide } from "@/features/settings/QuickGuide";
import { apiErrorMessage } from "@/lib/api/errors";
import { useContactSearch } from "@/features/contacts/api";
import { BulkActionsBar } from "@/features/contacts/BulkActionsBar";
import { ImportWizard } from "@/features/contacts/ImportWizard";
import { CreateContactDialog } from "@/features/contacts/CreateContactDialog";
import { buildRules, hasActiveFilters, type ContactFilters } from "@/features/contacts/buildRules";
import { ContactsTable } from "@/features/contacts/ContactsTable";
import { ContactSavedViews } from "@/features/contacts/ContactSavedViews";
import { ContactsActions } from "@/features/contacts/ContactsActions";
import { ContactsToolbar } from "@/features/contacts/ContactsToolbar";
import { useCustomAttributeDefinitions, useTags } from "@/features/customer-profile/api";
import { useHasPermission } from "@/lib/auth";

const PAGE_SIZE = 25;

const MANAGE_OUTLINE_BUTTON =
  "inline-flex h-[37px] items-center gap-1.5 rounded-md border border-[rgba(10,71,76,0.5)] px-3 text-sm font-medium text-[var(--color-nav-bg)] transition-colors hover:bg-[#ebf5f3] dark:text-accent";

const SALE_FILTERS = [
  { label: "All status", value: "", pill: "bg-surface text-[#4a4a4a] dark:bg-surface-2 dark:text-text-secondary" },
  ...SALE_STATUS_OPTIONS.map((option) => ({ label: option.label, value: option.value as string, pill: option.pill })),
];

function filtersToParams(filters: ContactFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("q", filters.search.trim());
  if (filters.tagId) params.set("tag", filters.tagId);
  if (filters.sale) params.set("sale", filters.sale);
  for (const [key, value] of Object.entries(filters.attributes)) {
    if (value) params.set(`attr_${key}`, value);
  }
  return params;
}

/** A table-shaped skeleton so the page keeps its layout while the first page loads. */
function LoadingRows(): JSX.Element {
  return (
    <div className="overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-3 border-b border-border px-4 py-3.5 last:border-0">
          <Skeleton className="h-4 w-4" />
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-3.5 w-32 sm:w-40" />
          <Skeleton className="ml-auto hidden h-3.5 w-28 sm:block" />
          <Skeleton className="h-5 w-20 rounded-full" />
        </div>
      ))}
    </div>
  );
}

/** The Contacts list: server-backed search/filter/pagination via the generated client, with search,
 *  tag + attribute filters, cursor pagination, client-side bulk selection, and URL-persisted state. */
export function ContactsList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  /** Room the docked bulk bar needs on phones — reported by the bar, which knows its own height. */
  const [dockedSpace, setDockedSpace] = useState(0);
  const [importing, setImporting] = useState(false);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState(false);
  const canCreate = useHasPermission("contacts:write");
  const canImport = useHasPermission("contacts:import");
  const canBroadcast = useHasPermission("campaigns:read");

  const filters = useMemo<ContactFilters>(() => {
    const attributes: Record<string, string> = {};
    for (const [key, value] of searchParams.entries()) {
      if (key.startsWith("attr_")) attributes[key.slice(5)] = value;
    }
    return {
      search: searchParams.get("q") ?? "",
      tagId: searchParams.get("tag") ?? "",
      sale: searchParams.get("sale") ?? "",
      attributes,
    };
  }, [searchParams]);
  const cursor = searchParams.get("cursor");

  const tags = useTags();
  const definitions = useCustomAttributeDefinitions();
  const enumAttributes = (definitions.data ?? []).filter((def) => def.data_type === "enum");
  const reactivationKey =
    enumAttributes.find((def) => /reactivat/i.test(def.key_name) || /reactivat/i.test(def.label))
      ?.key_name ?? null;

  const rules = buildRules(filters, tags.data ?? [], definitions.data ?? []);
  const contacts = useContactSearch({ rules, cursor, limit: PAGE_SIZE });

  const rows = contacts.data?.data ?? [];
  const page = contacts.data?.page;

  function applyFilters(next: ContactFilters): void {
    setSearchParams(filtersToParams(next)); // drops the cursor → back to the first page
  }

  function goToCursor(next: string): void {
    const params = filtersToParams(filters);
    params.set("cursor", next);
    setSearchParams(params);
  }

  function toggle(id: string): void {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll(): void {
    setSelectedIds((prev) => {
      const allSelected = rows.length > 0 && rows.every((contact) => prev.has(contact.id));
      const next = new Set(prev);
      for (const contact of rows) {
        if (allSelected) next.delete(contact.id);
        else next.add(contact.id);
      }
      return next;
    });
  }

  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Contacts" />
      <div className="space-y-4 px-4 py-6 sm:px-[30px]" style={{ paddingBottom: dockedSpace || undefined }}>
        <QuickGuide
          eyebrow="Contacts quick guide"
          text="All your customers in one place: search, filter by tag or sale status, import a sheet, or open a customer to see their chats and details."
        />

        <div className="flex flex-wrap items-center gap-2">
          <p className="mr-auto text-sm text-[#6e6e6e] dark:text-text-secondary">
            {page?.total != null ? `${page.total.toLocaleString("en-IN")} contacts` : "Contacts"}
          </p>
          {canBroadcast ? (
            <Link to="/broadcasts" className={MANAGE_OUTLINE_BUTTON}>
              <Megaphone aria-hidden className="h-4 w-4" /> Broadcast
            </Link>
          ) : null}
          {canCreate ? (
            <button type="button" onClick={() => { setCreated(false); setCreating(true); }} className={MANAGE_OUTLINE_BUTTON}>
              <Plus aria-hidden className="h-4 w-4" /> Add Contact
            </button>
          ) : null}
          {canImport ? (
            <button type="button" onClick={() => setImporting(true)} className={MANAGE_PRIMARY_ACTION}>
              <Upload aria-hidden className="mr-1 h-4 w-4" /> Import
            </button>
          ) : null}
          <ContactsActions rules={rules} />
        </div>

        {created ? <p role="status" className="mb-4 text-sm text-text-secondary">Contact created. Your current filters are preserved; clear them if the new contact is not visible.</p> : null}
        {creating ? <CreateContactDialog onClose={() => setCreating(false)} onCreated={() => { setCreating(false); setCreated(true); }} /> : null}
        {importing ? (
          <ImportWizard
            onClose={() => {
              setImporting(false);
              void contacts.refetch();
            }}
          />
        ) : null}

        <div className="mb-4 space-y-3">
          <ContactsToolbar
            filters={filters}
            onChange={applyFilters}
            tags={tags.data ?? []}
            enumAttributes={enumAttributes}
          />
          <div role="group" aria-label="Sale status" className="flex items-center gap-1.5 overflow-x-auto pb-1">
            {SALE_FILTERS.map((choice) => {
              const active = (filters.sale ?? "") === choice.value;
              return (
                <button
                  key={choice.label}
                  type="button"
                  aria-pressed={active}
                  onClick={() => applyFilters({ ...filters, sale: choice.value })}
                  className={`h-7 shrink-0 rounded-full px-3 text-xs font-medium transition-colors ${
                    active ? "bg-[var(--color-nav-bg)] text-white" : `${choice.pill} hover:opacity-80`
                  }`}
                >
                  {choice.label}
                </button>
              );
            })}
          </div>
          <ContactSavedViews filters={filters} onApply={applyFilters} />
        </div>

        <BulkActionsBar
          selectedIds={selectedIds}
          onClear={() => setSelectedIds(new Set())}
          rules={rules}
          onDockedHeightChange={setDockedSpace}
        />

        {contacts.isLoading ? (
          <LoadingRows />
        ) : contacts.isError ? (
          <ErrorState message={apiErrorMessage(contacts.error)} onRetry={() => void contacts.refetch()} />
        ) : rows.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface shadow-sm">
            <EmptyState
              icon={<ContactIcon className="h-6 w-6" />}
              title={hasActiveFilters(filters) ? "No contacts match your filters" : "No contacts yet"}
              description={
                hasActiveFilters(filters)
                  ? "Try a broader search or clear the filters to see everyone."
                  : "Import a CSV or add your first customer to start reactivating."
              }
              action={
                hasActiveFilters(filters) ? (
                  <Button variant="secondary" onClick={() => applyFilters({ search: "", tagId: "", sale: "", attributes: {} })}>
                    Clear filters
                  </Button>
                ) : canImport ? (
                  <Button leftIcon={<Upload className="h-4 w-4" />} onClick={() => setImporting(true)}>
                    Import your contacts
                  </Button>
                ) : undefined
              }
            />
          </div>
        ) : (
          <>
            <ContactsTable
              contacts={rows}
              selectedIds={selectedIds}
              onToggle={toggle}
              onToggleAll={toggleAll}
              reactivationKey={reactivationKey}
            />
            <Pagination
              label="Contact pagination"
              hasPrevious={Boolean(page?.prev_cursor)}
              hasNext={Boolean(page?.next_cursor)}
              onPrevious={() => {
                if (page?.prev_cursor) goToCursor(page.prev_cursor);
              }}
              onNext={() => {
                if (page?.next_cursor) goToCursor(page.next_cursor);
              }}
              summary={page?.total != null ? `${PAGE_SIZE} per page · ${page.total.toLocaleString("en-IN")} contacts` : undefined}
            />
          </>
        )}
      </div>
    </div>
  );
}
