import { Search, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import {
  Badge,
  Button,
  Field,
  FilterBar,
  Input,
  Modal,
  Select,
  ToolbarGroup,
} from "@/components/ui";
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

function activeFilterCount(filters: ContactFilters): number {
  return (filters.tagId ? 1 : 0) + Object.values(filters.attributes).filter(Boolean).length;
}

export function ContactsToolbar({ filters, onChange, tags, enumAttributes }: Props): JSX.Element {
  const compact = useIsCompact();
  const [sheetOpen, setSheetOpen] = useState(false);
  const activeCount = activeFilterCount(filters);

  const search = (
    <Input
      id="contacts-search"
      type="search"
      value={filters.search}
      onChange={(event) => onChange({ ...filters, search: event.target.value })}
      placeholder="Search name or number…"
      aria-label="Search contacts"
      leadingIcon={<Search aria-hidden className="h-4 w-4" />}
      containerClassName="min-w-[220px] flex-1"
    />
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
        <FilterBar label="Contact search and filters" contentClassName="w-full flex-nowrap">
          {search}
          <Button
            variant={activeCount > 0 ? "subtle" : "secondary"}
            leftIcon={<SlidersHorizontal className="h-4 w-4" />}
            onClick={() => setSheetOpen(true)}
            aria-expanded={sheetOpen}
          >
            Filters
            {activeCount > 0 ? <Badge tone="accent">{activeCount}</Badge> : null}
          </Button>
        </FilterBar>

        {sheetOpen ? (
          <Modal title="Filters" variant="sheet" onClose={() => setSheetOpen(false)}>
            <div className="space-y-4">
              <Field htmlFor="contacts-filter-tag" label="Tag">
                <Select
                  id="contacts-filter-tag"
                  value={filters.tagId}
                  onChange={(event) => setTag(event.target.value)}
                  disabled={tags.length === 0}
                >
                  <option value="">All tags</option>
                  {tags.map((tag) => (
                    <option key={tag.id} value={tag.id}>
                      {tag.name}
                    </option>
                  ))}
                </Select>
              </Field>

              {enumAttributes.map((attr) => (
                <Field key={attr.id} htmlFor={`contacts-filter-${attr.id}`} label={attr.label}>
                  <Select
                    id={`contacts-filter-${attr.id}`}
                    value={filters.attributes[attr.key_name] ?? ""}
                    onChange={(event) => setAttribute(attr.key_name, event.target.value)}
                  >
                    <option value="">All</option>
                    {(attr.enum_values ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </Select>
                </Field>
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
    <FilterBar label="Contact search and filters" contentClassName="w-full">
      {search}

      <ToolbarGroup className="shrink-0">
        <span className="inline-flex items-center gap-1.5 px-1 text-xs font-semibold text-text-secondary">
          <SlidersHorizontal aria-hidden className="h-4 w-4 text-text-disabled" />
          Filters
        </span>

        <Select
          aria-label="Filter by tag"
          value={filters.tagId}
          onChange={(event) => setTag(event.target.value)}
          disabled={tags.length === 0}
          className="min-w-[10rem] !w-auto"
        >
          <option value="">All tags</option>
          {tags.map((tag) => (
            <option key={tag.id} value={tag.id}>
              {tag.name}
            </option>
          ))}
        </Select>

        {enumAttributes.map((attr) => (
          <Select
            key={attr.id}
            aria-label={`Filter by ${attr.label}`}
            value={filters.attributes[attr.key_name] ?? ""}
            onChange={(event) => setAttribute(attr.key_name, event.target.value)}
            className="min-w-[10rem] !w-auto"
          >
            <option value="">{attr.label}: All</option>
            {(attr.enum_values ?? []).map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </Select>
        ))}
      </ToolbarGroup>
    </FilterBar>
  );
}
