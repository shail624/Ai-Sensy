import type { ContactFilters } from "@/features/contacts/buildRules";
import type { AttributeDefinition, Tag } from "@/features/contacts/types";

interface Props {
  filters: ContactFilters;
  onChange: (next: ContactFilters) => void;
  tags: Tag[];
  /** Enum custom-attribute definitions become filter dropdowns (Customer Type, Reactivation Status…). */
  enumAttributes: AttributeDefinition[];
}

export function ContactsToolbar({ filters, onChange, tags, enumAttributes }: Props): JSX.Element {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="contacts-search" className="text-xs font-medium text-text-secondary">
          Search
        </label>
        <input
          id="contacts-search"
          type="search"
          value={filters.search}
          onChange={(event) => onChange({ ...filters, search: event.target.value })}
          placeholder="Name or phone…"
          className="rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary"
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="contacts-tag" className="text-xs font-medium text-text-secondary">
          Tag
        </label>
        <select
          id="contacts-tag"
          value={filters.tagId}
          onChange={(event) => onChange({ ...filters, tagId: event.target.value })}
          disabled={tags.length === 0}
          className="rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary disabled:opacity-50"
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
        <div key={attr.id} className="flex flex-col gap-1">
          <label htmlFor={`attr-${attr.key_name}`} className="text-xs font-medium text-text-secondary">
            {attr.label}
          </label>
          <select
            id={`attr-${attr.key_name}`}
            value={filters.attributes[attr.key_name] ?? ""}
            onChange={(event) =>
              onChange({
                ...filters,
                attributes: { ...filters.attributes, [attr.key_name]: event.target.value },
              })
            }
            className="rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary"
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

      <div className="flex flex-col gap-1">
        <label htmlFor="contacts-sort" className="text-xs font-medium text-text-disabled">
          Sort
        </label>
        <select
          id="contacts-sort"
          disabled
          title="Sorting is not available on the contacts search API contract."
          className="cursor-not-allowed rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-disabled"
        >
          <option>Default</option>
        </select>
      </div>
    </div>
  );
}
