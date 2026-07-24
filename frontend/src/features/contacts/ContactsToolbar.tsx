import { Search, SlidersHorizontal } from "lucide-react";

import type { ContactFilters } from "@/features/contacts/buildRules";
import type { AttributeDefinition, Tag } from "@/features/contacts/types";

interface Props {
  filters: ContactFilters;
  onChange: (next: ContactFilters) => void;
  tags: Tag[];
  /** Enum custom-attribute definitions become filter dropdowns (Customer Type, Reactivation Status…). */
  enumAttributes: AttributeDefinition[];
}

const SELECT =
  "h-9 rounded-lg border border-border bg-surface px-3 text-sm font-medium text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-50";

export function ContactsToolbar({ filters, onChange, tags, enumAttributes }: Props): JSX.Element {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      {/* Search */}
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

      <SlidersHorizontal aria-hidden className="h-4 w-4 text-text-disabled" />

      {/* Tag filter */}
      <select
        aria-label="Filter by tag"
        value={filters.tagId}
        onChange={(event) => onChange({ ...filters, tagId: event.target.value })}
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
          onChange={(event) =>
            onChange({
              ...filters,
              attributes: { ...filters.attributes, [attr.key_name]: event.target.value },
            })
          }
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
