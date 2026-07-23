import type { CampaignListQuery, CampaignSort } from "@/features/campaigns/types";
import { CAMPAIGN_STATUS_LABELS, CAMPAIGN_STATUSES } from "@/features/campaigns/types";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORT_OPTIONS: { value: CampaignSort; label: string }[] = [
  { value: "-created_at", label: "Newest" },
  { value: "created_at", label: "Oldest" },
  { value: "name", label: "Name (A–Z)" },
  { value: "-name", label: "Name (Z–A)" },
  { value: "-total_recipients", label: "Largest audience" },
];

interface Props {
  filters: CampaignListQuery;
  onChange: (next: CampaignListQuery) => void;
}

/** Search, status and sort — one control each, matching the task list's toolbar. */
export function CampaignFilters({ filters, onChange }: Props): JSX.Element {
  function set<K extends keyof CampaignListQuery>(key: K, value: CampaignListQuery[K]): void {
    // Any filter change returns to the first page: page 3 of the old result set means nothing.
    onChange({ ...filters, [key]: value, page: 1 });
  }

  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
        <label htmlFor="campaigns-search" className="text-xs font-medium text-text-secondary">
          Search
        </label>
        <input
          id="campaigns-search"
          type="search"
          value={filters.q}
          onChange={(event) => set("q", event.target.value)}
          placeholder="Campaign name…"
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="campaigns-status" className="text-xs font-medium text-text-secondary">
          Status
        </label>
        <select
          id="campaigns-status"
          value={filters.status}
          onChange={(event) => set("status", event.target.value)}
          className={FIELD_CLASS}
        >
          <option value="">All statuses</option>
          {CAMPAIGN_STATUSES.map((status) => (
            <option key={status} value={status}>
              {CAMPAIGN_STATUS_LABELS[status]}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="campaigns-sort" className="text-xs font-medium text-text-secondary">
          Sort
        </label>
        <select
          id="campaigns-sort"
          value={filters.sort}
          onChange={(event) => set("sort", event.target.value as CampaignSort)}
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
