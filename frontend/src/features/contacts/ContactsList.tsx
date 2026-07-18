import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage } from "@/lib/api/errors";
import { useContactSearch } from "@/features/contacts/api";
import {
  buildRules,
  hasActiveFilters,
  type ContactFilters,
} from "@/features/contacts/buildRules";
import { ContactsTable } from "@/features/contacts/ContactsTable";
import { ContactsToolbar } from "@/features/contacts/ContactsToolbar";
import {
  useCustomAttributeDefinitions,
  useTags,
} from "@/features/customer-profile/api";

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

/** The Contacts list: server-backed search/filter/pagination via the generated client, with search,
 *  tag + attribute filters, cursor pagination, client-side bulk selection, and URL-persisted state. */
export function ContactsList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

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
    enumAttributes.find(
      (def) => /reactivat/i.test(def.key_name) || /reactivat/i.test(def.label),
    )?.key_name ?? null;

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
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <header className="mb-4">
        <h2 className="text-xl font-bold text-text-primary">Contacts</h2>
      </header>

      <div className="mb-4">
        <ContactsToolbar
          filters={filters}
          onChange={applyFilters}
          tags={tags.data ?? []}
          enumAttributes={enumAttributes}
        />
      </div>

      {selectedIds.size > 0 ? (
        <div className="mb-3 flex items-center justify-between rounded-md border border-border bg-surface-2 px-3 py-2 text-sm">
          <span>{selectedIds.size} selected</span>
          <button type="button" onClick={() => setSelectedIds(new Set())} className="text-accent hover:underline">
            Clear
          </button>
        </div>
      ) : null}

      {contacts.isLoading ? (
        <Spinner label="Loading contacts…" />
      ) : contacts.isError ? (
        <ErrorState message={apiErrorMessage(contacts.error)} onRetry={() => void contacts.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState
          title={hasActiveFilters(filters) ? "No contacts match your filters" : "No contacts yet"}
        />
      ) : (
        <>
          <ContactsTable
            contacts={rows}
            selectedIds={selectedIds}
            onToggle={toggle}
            onToggleAll={toggleAll}
            reactivationKey={reactivationKey}
          />
          <nav aria-label="Pagination" className="mt-3 flex items-center justify-end gap-2">
            <button
              type="button"
              disabled={!page?.prev_cursor}
              onClick={() => {
                if (page?.prev_cursor) goToCursor(page.prev_cursor);
              }}
              className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
            >
              Previous
            </button>
            <button
              type="button"
              disabled={!page?.next_cursor}
              onClick={() => {
                if (page?.next_cursor) goToCursor(page.next_cursor);
              }}
              className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
            >
              Next
            </button>
          </nav>
        </>
      )}
    </div>
  );
}
