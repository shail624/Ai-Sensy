import type { TemplateListQuery, TemplateSort } from "@/features/templates/types";
import {
  CATEGORIES,
  CATEGORY_LABELS,
  STATUS_LABELS,
  STATUSES,
} from "@/features/templates/types";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

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
}

/** Search, approval status, category, language and sort — one control each. */
export function TemplateFilters({ filters, languages, onChange }: Props): JSX.Element {
  function set<K extends keyof TemplateListQuery>(key: K, value: TemplateListQuery[K]): void {
    // Any filter change returns to the first page: page 3 of the old result set means nothing.
    onChange({ ...filters, [key]: value, page: 1 });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
        <label htmlFor="templates-search" className="text-xs font-medium text-text-secondary">
          Search
        </label>
        <input
          id="templates-search"
          type="search"
          value={filters.q}
          onChange={(event) => set("q", event.target.value)}
          placeholder="Template name…"
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="templates-status" className="text-xs font-medium text-text-secondary">
          Approval status
        </label>
        <select
          id="templates-status"
          value={filters.status}
          onChange={(event) => set("status", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All statuses</option>
          {STATUSES.map((status) => (
            <option key={status} value={status}>
              {STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="templates-category" className="text-xs font-medium text-text-secondary">
          Category
        </label>
        <select
          id="templates-category"
          value={filters.category}
          onChange={(event) => set("category", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All categories</option>
          {CATEGORIES.map((category) => (
            <option key={category} value={category}>
              {CATEGORY_LABELS[category]}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="templates-language" className="text-xs font-medium text-text-secondary">
          Language
        </label>
        <select
          id="templates-language"
          value={filters.language}
          onChange={(event) => set("language", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All languages</option>
          {languages.map((language) => (
            <option key={language} value={language}>
              {language}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="templates-sort" className="text-xs font-medium text-text-secondary">
          Sort
        </label>
        <select
          id="templates-sort"
          value={filters.sort}
          onChange={(event) => set("sort", event.target.value as TemplateSort)}
          className={FIELD_CLASS}
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
