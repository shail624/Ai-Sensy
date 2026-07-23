import type { MediaListQuery, MediaSort } from "@/features/media/types";
import { MEDIA_TYPE_LABELS, MEDIA_TYPES } from "@/features/media/types";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORT_OPTIONS: { value: MediaSort; label: string }[] = [
  { value: "-created_at", label: "Newest" },
  { value: "created_at", label: "Oldest" },
  { value: "name", label: "Name (A–Z)" },
  { value: "-byte_size", label: "Largest" },
  { value: "byte_size", label: "Smallest" },
];

interface Props {
  filters: MediaListQuery;
  onChange: (next: MediaListQuery) => void;
}

/** Search, media type and sort — one control each, matching the campaign and template toolbars. */
export function MediaFilters({ filters, onChange }: Props): JSX.Element {
  function set<K extends keyof MediaListQuery>(key: K, value: MediaListQuery[K]): void {
    // Any filter change returns to the first page: page 3 of the old result set means nothing.
    onChange({ ...filters, [key]: value, page: 1 });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
        <label htmlFor="media-search" className="text-xs font-medium text-text-secondary">
          Search
        </label>
        <input
          id="media-search"
          type="search"
          value={filters.q}
          onChange={(event) => set("q", event.target.value)}
          placeholder="File name, ID or hash…"
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="media-type-filter" className="text-xs font-medium text-text-secondary">
          Type
        </label>
        <select
          id="media-type-filter"
          value={filters.mediaType}
          onChange={(event) => set("mediaType", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All types</option>
          {MEDIA_TYPES.map((type) => (
            <option key={type} value={type}>
              {MEDIA_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="media-sort" className="text-xs font-medium text-text-secondary">
          Sort
        </label>
        <select
          id="media-sort"
          value={filters.sort}
          onChange={(event) => set("sort", event.target.value as MediaSort)}
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
