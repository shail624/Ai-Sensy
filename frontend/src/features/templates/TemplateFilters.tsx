import { Search } from "lucide-react";
import type { ReactNode } from "react";

import type { TemplateListQuery, TemplateSort } from "@/features/templates/types";
import { CATEGORIES, CATEGORY_LABELS, STATUS_TABS } from "@/features/templates/types";

const SELECT_CLASS =
  "h-9 rounded-md border border-[#e8e8e8] bg-surface px-2 text-sm text-[#4a4a4a] transition-colors hover:border-[#cfcfcf] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:border-border dark:text-text-primary";

const SORT_OPTIONS: { value: TemplateSort; label: string }[] = [
  { value: "-created_at", label: "Newest" },
  { value: "created_at", label: "Oldest" },
  { value: "-updated_at", label: "Recently updated" },
  { value: "name", label: "Name (A–Z)" },
  { value: "-name", label: "Name (Z–A)" },
];

interface Props {
  filters: TemplateListQuery;
  /** Languages actually present in the registry — no point offering one nothing uses. */
  languages: string[];
  onChange: (next: TemplateListQuery) => void;
  /** Right-aligned actions on the search row (the reference's "Sync Status"). */
  actions?: ReactNode;
}

/**
 * The reference layout: a search pill with the finer category/language/sort controls and the page
 * action on one row, then status as tabs with a sliding indicator.
 */
export function TemplateFilters({ filters, languages, onChange, actions }: Props): JSX.Element {
  function set<K extends keyof TemplateListQuery>(key: K, value: TemplateListQuery[K]): void {
    // Any filter change returns to the first page: page 3 of the old result set means nothing.
    onChange({ ...filters, [key]: value, page: 1 });
  }

  const activeIndex = Math.max(0, STATUS_TABS.findIndex((tab) => tab.value === filters.status));

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex h-10 w-full max-w-[300px] items-center gap-2 rounded-[8px] bg-surface px-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <label htmlFor="templates-search" className="sr-only">Search</label>
          <input
            id="templates-search"
            type="search"
            value={filters.q}
            onChange={(event) => set("q", event.target.value)}
            placeholder="Search templates (status, name etc.)"
            className="h-full min-w-0 flex-1 bg-transparent text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus:outline-none dark:text-text-primary"
          />
          <Search aria-hidden className="h-4 w-4 shrink-0 text-black/40" />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label htmlFor="templates-category" className="sr-only">Category</label>
          <select id="templates-category" value={filters.category} onChange={(event) => set("category", event.target.value)} className={SELECT_CLASS}>
            <option value="">All categories</option>
            {CATEGORIES.map((category) => (
              <option key={category} value={category}>{CATEGORY_LABELS[category]}</option>
            ))}
          </select>
          <label htmlFor="templates-language" className="sr-only">Language</label>
          <select id="templates-language" value={filters.language} onChange={(event) => set("language", event.target.value)} className={SELECT_CLASS}>
            <option value="">All languages</option>
            {languages.map((language) => (
              <option key={language} value={language}>{language}</option>
            ))}
          </select>
          <label htmlFor="templates-sort" className="sr-only">Sort</label>
          <select id="templates-sort" value={filters.sort} onChange={(event) => set("sort", event.target.value as TemplateSort)} className={SELECT_CLASS}>
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
          {actions}
        </div>
      </div>

      <div className="border-b border-[#e8e8e8] dark:border-border">
        <div role="tablist" aria-label="Approval status" className="relative flex overflow-x-auto">
          {STATUS_TABS.map((tab) => {
            const selected = tab.value === filters.status;
            return (
              <button
                key={tab.label}
                type="button"
                role="tab"
                aria-selected={selected}
                onClick={() => set("status", tab.value)}
                className={`h-12 w-40 shrink-0 px-3 text-sm font-medium transition-colors duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus ${
                  selected ? "text-[var(--color-nav-bg)] dark:text-accent" : "text-[#6e6e6e] hover:text-[#4a4a4a] dark:text-text-secondary"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
          <span
            aria-hidden
            className="absolute bottom-0 h-[3px] w-40 rounded-t-[3px] bg-[var(--color-nav-bg)] transition-[left] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] dark:bg-accent"
            style={{ left: `${activeIndex * 160}px` }}
          />
        </div>
      </div>
    </div>
  );
}
