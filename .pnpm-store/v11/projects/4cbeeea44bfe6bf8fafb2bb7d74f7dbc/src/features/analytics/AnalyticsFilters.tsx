import type {
  AnalyticsFilterState,
  Compare,
  Granularity,
  Preset,
} from "@/features/analytics/types";
import { COMPARISONS, GRANULARITIES, PRESETS } from "@/features/analytics/types";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

interface Props {
  filters: AnalyticsFilterState;
  onChange: (next: AnalyticsFilterState) => void;
}

/**
 * The Doc 15 §14.2 filter surface: preset **or** an explicit range, plus granularity and an
 * optional comparison window. Choosing a preset clears the explicit dates and vice versa — the API
 * takes one or the other, and offering both at once would be ambiguous.
 */
export function AnalyticsFilters({ filters, onChange }: Props): JSX.Element {
  return (
    <div className="flex flex-wrap items-end gap-3">
      <div className="flex flex-col gap-1">
        <label htmlFor="analytics-preset" className="text-xs font-medium text-text-secondary">
          Period
        </label>
        <select
          id="analytics-preset"
          value={filters.preset}
          onChange={(event) =>
            onChange({
              ...filters,
              preset: event.target.value as Preset | "",
              from: "",
              to: "",
            })
          }
          className={FIELD_CLASS}
        >
          <option value="">Custom range</option>
          {PRESETS.map((preset) => (
            <option key={preset.value} value={preset.value}>
              {preset.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="analytics-from" className="text-xs font-medium text-text-secondary">
          From
        </label>
        <input
          id="analytics-from"
          type="date"
          value={filters.from.slice(0, 10)}
          onChange={(event) =>
            onChange({
              ...filters,
              preset: "",
              from: event.target.value ? `${event.target.value}T00:00:00Z` : "",
            })
          }
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="analytics-to" className="text-xs font-medium text-text-secondary">
          To
        </label>
        <input
          id="analytics-to"
          type="date"
          value={filters.to.slice(0, 10)}
          onChange={(event) =>
            onChange({
              ...filters,
              preset: "",
              to: event.target.value ? `${event.target.value}T23:59:59Z` : "",
            })
          }
          className={FIELD_CLASS}
        />
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="analytics-granularity" className="text-xs font-medium text-text-secondary">
          Granularity
        </label>
        <select
          id="analytics-granularity"
          value={filters.granularity}
          onChange={(event) =>
            onChange({ ...filters, granularity: event.target.value as Granularity })
          }
          className={FIELD_CLASS}
        >
          {GRANULARITIES.map((granularity) => (
            <option key={granularity.value} value={granularity.value}>
              {granularity.label}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-1">
        <label htmlFor="analytics-compare" className="text-xs font-medium text-text-secondary">
          Compare
        </label>
        <select
          id="analytics-compare"
          value={filters.compare}
          onChange={(event) => onChange({ ...filters, compare: event.target.value as Compare | "" })}
          className={FIELD_CLASS}
        >
          <option value="">No comparison</option>
          {COMPARISONS.map((comparison) => (
            <option key={comparison.value} value={comparison.value}>
              {comparison.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
