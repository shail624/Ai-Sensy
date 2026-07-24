import { Contact as ContactIcon } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { Badge, Button, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api/errors";
import { useContactSearch } from "@/features/contacts/api";
import { BulkActionsBar } from "@/features/contacts/BulkActionsBar";
import { buildRules, hasActiveFilters, type ContactFilters } from "@/features/contacts/buildRules";
import { ContactsTable } from "@/features/contacts/ContactsTable";
import { ContactsToolbar } from "@/features/contacts/ContactsToolbar";
import { useCustomAttributeDefinitions, useTags } from "@/features/customer-profile/api";

const PAGE_SIZE = 25;

function filtersToParams(filters: ContactFilters): URLSearchParams {
  const params = new URLSearchParams();
  if (filters.search.trim()) params.set("q", filters.search.trim());
  if (filters.tagId) params.set("tag", filters.tagId);
  for (const [key, value] of Object.entries(filters.attributes)) {
    if (value) params.set(`attr_${key}`, value);
  }
  return params;
}

/** A table-shaped skeleton so the page keeps its layout while the first page loads. */
function LoadingRows(): JSX.Element {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
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

  const filters = useMemo<ContactFilters>(() => {
    const attributes: Record<string, string> = {};
    for (const [key, value] of searchParams.entries()) {
      if (key.startsWith("attr_")) attributes[key.slice(5)] = value;
    }
    return {
      search: searchParams.get("q") ?? "",
      tagId: searchParams.get("tag") ?? "",
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
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6" style={{ paddingBottom: 24 + dockedSpace }}>
      {/* Header */}
      <header className="mb-5 flex items-center gap-3">
        <h1 className="text-2xl font-bold tracking-tight text-text-primary">Contacts</h1>
        {page?.total != null ? (
          <Badge tone="neutral">{page.total.toLocaleString()}</Badge>
        ) : null}
      </header>

      {/* Search + filters */}
      <div className="mb-4">
        <ContactsToolbar
          filters={filters}
          onChange={applyFilters}
          tags={tags.data ?? []}
          enumAttributes={enumAttributes}
        />
      </div>

      {/* Bulk actions — docked to the bottom edge on phones (DS-14), inline from `md` up. */}
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
        <div className="rounded-2xl border border-border bg-surface shadow-sm">
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
                <Button variant="secondary" onClick={() => applyFilters({ search: "", tagId: "", attributes: {} })}>
                  Clear filters
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
          <nav aria-label="Pagination" className="mt-4 flex items-center justify-end gap-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={!page?.prev_cursor}
              onClick={() => {
                if (page?.prev_cursor) goToCursor(page.prev_cursor);
              }}
            >
              Previous
            </Button>
            <Button
              variant="secondary"
              size="sm"
              disabled={!page?.next_cursor}
              onClick={() => {
                if (page?.next_cursor) goToCursor(page.next_cursor);
              }}
            >
              Next
            </Button>
          </nav>
        </>
      )}
    </div>
  );
}
