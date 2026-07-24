import { Search, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import { Badge, Button, Modal } from "@/components/ui";
import type { ContactFilters } from "@/features/contacts/buildRules";
import type { AttributeDefinition, Tag } from "@/features/contacts/types";
import { useIsCompact } from "@/lib/useMediaQuery";

interface Props {
  filters: ContactFilters;
  onChange: (next: ContactFilters) => void;
  tags: Tag[];
  /** Enum custom-attribute definitions become filter dropdowns (Customer Type, Reactivation Status…). */
  enumAttributes: AttributeDefinition[];
}

const SELECT =
  "h-9 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-50";

function activeFilterCount(filters: ContactFilters): number {
  return (filters.tagId ? 1 : 0) + Object.values(filters.attributes).filter(Boolean).length;
}

export function ContactsToolbar({ filters, onChange, tags, enumAttributes }: Props): JSX.Element {
  const compact = useIsCompact();
  const [sheetOpen, setSheetOpen] = useState(false);
  const activeCount = activeFilterCount(filters);

  const search = (
    <div className="relative min-w-[220px] flex-1">
      <label htmlFor="contacts-search" className="sr-only">
        Search contacts
      </label>
      <Search
        aria-hidden
        className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-disabled"
      />
      <input
        id="contacts-search"
        type="search"
        value={filters.search}
        onChange={(event) => onChange({ ...filters, search: event.target.value })}
        placeholder="Search name or number…"
        className="h-9 w-full rounded-lg border border-border bg-surface pl-9 pr-3 text-sm text-text-primary placeholder:text-text-disabled focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      />
    </div>
  );

  function setTag(value: string): void {
    onChange({ ...filters, tagId: value });
  }

  function setAttribute(key: string, value: string): void {
    onChange({ ...filters, attributes: { ...filters.attributes, [key]: value } });
  }

  // Below `md` the dropdowns move into a bottom sheet so the list keeps the viewport (Doc 05 B3.1).
  if (compact) {
    return (
      <>
        <div className="flex items-center gap-2">
          {search}
          <Button
            variant="secondary"
            leftIcon={<SlidersHorizontal className="h-4 w-4" />}
            onClick={() => setSheetOpen(true)}
            aria-expanded={sheetOpen}
          >
            Filters
            {activeCount > 0 ? <Badge tone="accent">{activeCount}</Badge> : null}
          </Button>
        </div>

        {sheetOpen ? (
          <Modal title="Filters" variant="sheet" onClose={() => setSheetOpen(false)}>
            <div className="space-y-3.5">
              <div>
                <label htmlFor="contacts-filter-tag" className="mb-1 block text-xs font-semibold text-text-secondary">
                  Tag
                </label>
                <select
                  id="contacts-filter-tag"
                  value={filters.tagId}
                  onChange={(event) => setTag(event.target.value)}
                  disabled={tags.length === 0}
                  className={`${SELECT} w-full`}
                >
                  <option value="">All tags</option>
                  {tags.map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.name}
                    </option>
                  ))}
                </select>
              </div>

              {enumAttributes.map((attr) => (
                <div key={attr.id}>
                  <label
                    htmlFor={`contacts-filter-${attr.id}`}
                    className="mb-1 block text-xs font-semibold text-text-secondary"
                  >
                    {attr.label}
                  </label>
                  <select
                    id={`contacts-filter-${attr.id}`}
                    value={filters.attributes[attr.key_name] ?? ""}
                    onChange={(event) => setAttribute(attr.key_name, event.target.value)}
                    className={`${SELECT} w-full`}
                  >
                    <option value="">All</option>
                    {(attr.enum_values ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>

            <div className="mt-5 flex gap-2 border-t border-border pt-4">
              <Button
                variant="secondary"
                block
                disabled={activeCount === 0}
                onClick={() => onChange({ ...filters, tagId: "", attributes: {} })}
              >
                Clear all
              </Button>
              <Button block onClick={() => setSheetOpen(false)}>
                Show results
              </Button>
            </div>
          </Modal>
        ) : null}
      </>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2.5">
      {search}

      <SlidersHorizontal aria-hidden className="h-4 w-4 text-text-disabled" />

      {/* Tag filter */}
      <select
        aria-label="Filter by tag"
        value={filters.tagId}
        onChange={(event) => setTag(event.target.value)}
        disabled={tags.length === 0}
        className={SELECT}
      >
        <option value="">All tags</option>
        {tags.map((tag) => (
          <option key={tag.id} value={tag.id}>
            {tag.name}
          </option>
        ))}
      </select>

      {/* Enum custom-attribute filters */}
      {enumAttributes.map((attr) => (
        <select
          key={attr.id}
          aria-label={`Filter by ${attr.label}`}
          value={filters.attributes[attr.key_name] ?? ""}
          onChange={(event) => setAttribute(attr.key_name, event.target.value)}
          className={SELECT}
        >
          <option value="">{attr.label}: All</option>
          {(attr.enum_values ?? []).map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      ))}
    </div>
  );
}
