import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useHasPermission, useWabas } from "@/features/channels/api";
import { TokenChip, WabaStatusChip } from "@/features/channels/ChannelBadges";
import { selectWabas, wabaSummary } from "@/features/channels/selectors";
import { WabaActions } from "@/features/channels/WabaActions";
import { WabaFormDialog } from "@/features/channels/WabaFormDialog";
import type { WabaListQuery, WabaSort } from "@/features/channels/types";
import { DEFAULT_WABA_QUERY, WABA_STATUS_LABELS, WABA_STATUSES } from "@/features/channels/types";
import { formatCount, formatDate } from "@/lib/format";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

const SORTS: WabaSort[] = ["name", "-name", "-created_at", "-numbers"];

const SORT_LABELS: Record<WabaSort, string> = {
  name: "Name (A–Z)",
  "-name": "Name (Z–A)",
  "-created_at": "Recently connected",
  "-numbers": "Most numbers",
};

function readQuery(params: URLSearchParams): WabaListQuery {
  const status = params.get("status") ?? "";
  const sort = params.get("sort") ?? "";
  return {
    q: params.get("q") ?? "",
    // Anything outside the known vocabulary is ignored rather than filtering everything out.
    status: WABA_STATUSES.includes(status) ? status : "",
    sort: SORTS.includes(sort as WabaSort) ? (sort as WabaSort) : DEFAULT_WABA_QUERY.sort,
  };
}

function writeQuery(query: WabaListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.status) params.set("status", query.status);
  if (query.sort !== DEFAULT_WABA_QUERY.sort) params.set("sort", query.sort);
  return params;
}

/**
 * Connected WhatsApp Business Accounts (Doc 05 B11.5).
 *
 * `GET /waba` returns the organization's complete list with no paging of any kind, so there is no
 * page boundary to warn about here — searching and filtering run over everything there is.
 */
export function WabaList(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [connecting, setConnecting] = useState(false);

  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const canManage = useHasPermission("waba:manage");

  const wabas = useWabas();
  const all = useMemo(() => wabas.data ?? [], [wabas.data]);
  const rows = useMemo(() => selectWabas(all, query), [all, query]);
  const summary = useMemo(() => wabaSummary(all), [all]);

  const isFiltered = query.q !== "" || query.status !== "";

  function apply(next: Partial<WabaListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next }));
  }

  if (wabas.isLoading) return <Spinner label="Loading accounts…" />;

  if (wabas.isError) {
    return <ErrorState message={apiErrorMessage(wabas.error)} onRetry={() => void wabas.refetch()} />;
  }

  return (
    <>
      {all.length > 0 ? (
        <p className="mb-3 text-sm text-text-secondary">
          {formatCount(summary.total)} account{summary.total === 1 ? "" : "s"} ·{" "}
          {formatCount(summary.active)} active · {formatCount(summary.numbers)} number
          {summary.numbers === 1 ? "" : "s"}
          {summary.needsAttention > 0
            ? ` · ${formatCount(summary.needsAttention)} needing credential attention`
            : ""}
        </p>
      ) : null}

      <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
            <label htmlFor="waba-search" className="text-xs font-medium text-text-secondary">
              Search
            </label>
            <input
              id="waba-search"
              type="search"
              value={query.q}
              onChange={(event) => apply({ q: event.target.value })}
              placeholder="Business name or WABA id…"
              className={FIELD_CLASS}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="waba-status-filter" className="text-xs font-medium text-text-secondary">
              Status
            </label>
            <select
              id="waba-status-filter"
              value={query.status}
              onChange={(event) => apply({ status: event.target.value })}
              className={FIELD_CLASS}
            >
              <option value="">All statuses</option>
              {WABA_STATUSES.map((status) => (
                <option key={status} value={status}>
                  {WABA_STATUS_LABELS[status]}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="waba-sort" className="text-xs font-medium text-text-secondary">
              Sort
            </label>
            <select
              id="waba-sort"
              value={query.sort}
              onChange={(event) => apply({ sort: event.target.value as WabaSort })}
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

        {canManage ? (
          <button
            type="button"
            onClick={() => setConnecting(true)}
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            Connect account
          </button>
        ) : null}
      </div>

      {all.length === 0 ? (
        <EmptyState
          title="No WhatsApp Business Accounts"
          description={
            canManage
              ? "Connect an account with its system-user token to start sending."
              : "No accounts have been connected yet."
          }
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No accounts match these filters"
          description="Try a different name, id or status."
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Account</th>
                  <th scope="col" className="px-3 py-2">Status</th>
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Credential</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Numbers</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Connected</th>
                  <th scope="col" className="px-3 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((waba) => (
                  <tr key={waba.id} className="border-b border-border last:border-0 hover:bg-hover">
                    <td className="px-3 py-2">
                      <Link
                        to={`/channels/accounts/${waba.id}`}
                        className="font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                      >
                        {waba.business_name}
                      </Link>
                      <p className="font-mono text-xs text-text-disabled">{waba.waba_id}</p>
                      <div className="mt-1 md:hidden">
                        <TokenChip waba={waba} />
                      </div>
                    </td>
                    <td className="px-3 py-2">
                      <WabaStatusChip value={waba.status} />
                    </td>
                    <td className="hidden px-3 py-2 md:table-cell">
                      <TokenChip waba={waba} />
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                      {formatCount(waba.phone_number_count)}
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
                      {formatDate(waba.created_at)}
                    </td>
                    <td className="px-3 py-2">
                      <WabaActions waba={waba} compact />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-3 text-sm text-text-secondary">
            {isFiltered ? "Matching: " : ""}
            {formatCount(rows.length)} account{rows.length === 1 ? "" : "s"}
          </p>
        </>
      )}

      {connecting ? <WabaFormDialog onClose={() => setConnecting(false)} /> : null}
    </>
  );
}
