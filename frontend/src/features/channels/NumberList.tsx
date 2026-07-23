import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useNumbers, useWabas } from "@/features/channels/api";
import {
  DefaultChip,
  MetaValueChip,
  NumberStatusChip,
  QualityChip,
} from "@/features/channels/ChannelBadges";
import { NumberActions } from "@/features/channels/NumberActions";
import { numberStatuses, numberSummary, selectNumbers } from "@/features/channels/selectors";
import type { NumberListQuery, NumberSort } from "@/features/channels/types";
import { DEFAULT_NUMBER_QUERY, QUALITY_RATINGS } from "@/features/channels/types";
import { formatCount, formatAge } from "@/lib/format";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORTS: NumberSort[] = ["number", "-number", "-quality", "-mps_limit"];

const SORT_LABELS: Record<NumberSort, string> = {
  number: "Number (A–Z)",
  "-number": "Number (Z–A)",
  "-quality": "Lowest quality first",
  "-mps_limit": "Highest limit",
};

function readQuery(params: URLSearchParams): NumberListQuery {
  const quality = params.get("quality") ?? "";
  const sort = params.get("sort") ?? "";
  return {
    q: params.get("q") ?? "",
    waba: params.get("waba") ?? "",
    status: params.get("status") ?? "",
    quality: QUALITY_RATINGS.includes(quality) ? quality : "",
    sort: SORTS.includes(sort as NumberSort) ? (sort as NumberSort) : DEFAULT_NUMBER_QUERY.sort,
  };
}

function writeQuery(query: NumberListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.waba) params.set("waba", query.waba);
  if (query.status) params.set("status", query.status);
  if (query.quality) params.set("quality", query.quality);
  if (query.sort !== DEFAULT_NUMBER_QUERY.sort) params.set("sort", query.sort);
  return params;
}

/**
 * Phone numbers across every connected account (Doc 05 B11.6).
 *
 * `GET /phone-numbers` applies no limit, so this list is the complete set and filtering over it is
 * exact. There is no "add number": numbers exist because a WABA sync found them at Meta, and the
 * platform neither creates nor deletes them.
 */
export function NumberList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = useMemo(() => readQuery(searchParams), [searchParams]);

  const numbers = useNumbers();
  const wabas = useWabas();

  const all = useMemo(() => numbers.data ?? [], [numbers.data]);
  const rows = useMemo(() => selectNumbers(all, query), [all, query]);
  const summary = useMemo(() => numberSummary(all), [all]);
  const statuses = useMemo(() => numberStatuses(all), [all]);

  const isFiltered =
    query.q !== "" || query.waba !== "" || query.status !== "" || query.quality !== "";

  function apply(next: Partial<NumberListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next }));
  }

  function wabaName(id: string): string {
    return (wabas.data ?? []).find((waba) => waba.id === id)?.business_name ?? id;
  }

  if (numbers.isLoading) return <Spinner label="Loading numbers…" />;

  if (numbers.isError) {
    return (
      <ErrorState message={apiErrorMessage(numbers.error)} onRetry={() => void numbers.refetch()} />
    );
  }

  return (
    <>
      {all.length > 0 ? (
        <p className="mb-3 text-sm text-text-secondary">
          {formatCount(summary.total)} number{summary.total === 1 ? "" : "s"} ·{" "}
          {formatCount(summary.healthy)} healthy · {formatCount(summary.capacity)} messages/second
          combined
          {summary.degraded > 0 ? ` · ${formatCount(summary.degraded)} rated RED` : ""}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
          <label htmlFor="number-search" className="text-xs font-medium text-text-secondary">
            Search
          </label>
          <input
            id="number-search"
            type="search"
            value={query.q}
            onChange={(event) => apply({ q: event.target.value })}
            placeholder="Number, display name or id…"
            className={FIELD_CLASS}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="number-waba" className="text-xs font-medium text-text-secondary">
            Account
          </label>
          <select
            id="number-waba"
            value={query.waba}
            onChange={(event) => apply({ waba: event.target.value })}
            className={FIELD_CLASS}
          >
            <option value="">All accounts</option>
            {(wabas.data ?? []).map((waba) => (
              <option key={waba.id} value={waba.id}>
                {waba.business_name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="number-status" className="text-xs font-medium text-text-secondary">
            Status
          </label>
          <select
            id="number-status"
            value={query.status}
            onChange={(event) => apply({ status: event.target.value })}
            className={FIELD_CLASS}
          >
            <option value="">All statuses</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="number-quality" className="text-xs font-medium text-text-secondary">
            Quality
          </label>
          <select
            id="number-quality"
            value={query.quality}
            onChange={(event) => apply({ quality: event.target.value })}
            className={FIELD_CLASS}
          >
            <option value="">Any rating</option>
            {QUALITY_RATINGS.map((rating) => (
              <option key={rating} value={rating}>
                {rating}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="number-sort" className="text-xs font-medium text-text-secondary">
            Sort
          </label>
          <select
            id="number-sort"
            value={query.sort}
            onChange={(event) => apply({ sort: event.target.value as NumberSort })}
            className={FIELD_CLASS}
          >
            {SORTS.map((sort) => (
              <option key={sort} value={sort}>
                {SORT_LABELS[sort]}
              </option>
            ))}
          </select>
        </div>
      </div>

      {all.length === 0 ? (
        <EmptyState
          title="No phone numbers"
          description="Numbers are pulled from Meta. Connect an account and use Sync numbers on it — they cannot be added by hand."
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No numbers match these filters"
          description="Try a different account, status or rating."
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Number</th>
                  <th scope="col" className="px-3 py-2">Status</th>
                  <th scope="col" className="hidden px-3 py-2 sm:table-cell">Quality</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Account</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Tier</th>
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Limit</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Synced</th>
                  <th scope="col" className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((number) => (
                  <tr key={number.id} className="border-b border-border last:border-0 hover:bg-hover">
                    <td className="px-3 py-2">
                      <Link
                        to={`/channels/numbers/${number.id}`}
                        className="font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                      >
                        {number.display_number}
                      </Link>
                      <p className="truncate text-xs text-text-secondary">
                        {number.verified_name ?? "No display name"}
                      </p>
                      <div className="mt-1 flex flex-wrap gap-1 sm:hidden">
                        <QualityChip value={number.quality_rating} />
                        {number.is_default ? <DefaultChip /> : null}
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <NumberStatusChip value={number.status} />
                    </td>
                    <td className="hidden px-3 py-2 sm:table-cell">
                      <div className="flex flex-wrap gap-1">
                        <QualityChip value={number.quality_rating} />
                        {number.is_default ? <DefaultChip /> : null}
                      </div>
                    </td>
                    <td className="hidden px-3 py-2 lg:table-cell">
                      <Link
                        to={`/channels/accounts/${number.waba_id}`}
                        className="text-text-secondary hover:text-accent"
                      >
                        {wabaName(number.waba_id)}
                      </Link>
                    </td>
                    <td className="hidden px-3 py-2 xl:table-cell">
                      <MetaValueChip value={number.messaging_tier} />
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                      {formatCount(number.mps_limit)}/s
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
                      {number.last_synced_at ? formatAge(number.last_synced_at) : "never"}
                    </td>
                    <td className="px-3 py-2">
                      <NumberActions number={number} compact />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-3 text-sm text-text-secondary">
            {isFiltered ? "Matching: " : ""}
            {formatCount(rows.length)} number{rows.length === 1 ? "" : "s"}
          </p>
        </>
      )}
    </>
  );
}
