import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { AdminPagination } from "@/features/admin/AdminPagination";
import { SecurityChip } from "@/features/admin/AdminBadges";
import { apiErrorMessage, useAuditLog } from "@/features/admin/api";
import { AuditDetailDialog } from "@/features/admin/AuditDetailDialog";
import { auditChanges, auditFacets, selectAuditPage } from "@/features/admin/selectors";
import type { AuditEntry, AuditListQuery } from "@/features/admin/types";
import { actionEntity, humanizeAction, isSecurityEvent } from "@/features/admin/types";
import { formatDateTime, UNKNOWN } from "@/lib/format";

const FIELD_CLASS =
  "rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";

function readQuery(params: URLSearchParams): AuditListQuery {
  const page = Number.parseInt(params.get("page") ?? "", 10);
  return {
    q: params.get("q") ?? "",
    action: params.get("action") ?? "",
    entity: params.get("entity") ?? "",
    actor: params.get("actor") ?? "",
    page: Number.isFinite(page) && page > 0 ? page : 1,
  };
}

function writeQuery(query: AuditListQuery): URLSearchParams {
  const params = new URLSearchParams();
  if (query.q) params.set("q", query.q);
  if (query.action) params.set("action", query.action);
  if (query.entity) params.set("entity", query.entity);
  if (query.actor) params.set("actor", query.actor);
  if (query.page > 1) params.set("page", String(query.page));
  return params;
}

/**
 * The audit trail (Doc 05 B11.10) — who did what, to which entity, when, and from where.
 *
 * The trail is append-only and immutable, so a loaded page never shifts under the reader. Filter
 * options are derived from the entries actually present rather than from the ~80-constant action
 * vocabulary, because offering codes this page will never show is a worse filter than offering
 * exactly what it holds.
 */
export function AuditPanel(): JSX.Element {
  const [searchParams, setSearchParams] = useSearchParams();
  const [inspecting, setInspecting] = useState<AuditEntry | null>(null);

  const query = useMemo(() => readQuery(searchParams), [searchParams]);
  const audit = useAuditLog();

  const entries = useMemo(() => audit.data?.data ?? [], [audit.data]);
  const facets = useMemo(() => auditFacets(entries), [entries]);
  const page = useMemo(() => selectAuditPage(entries, query), [entries, query]);
  const total = audit.data?.page.total ?? entries.length;

  const isFiltered =
    query.q !== "" || query.action !== "" || query.entity !== "" || query.actor !== "";

  function apply(next: Partial<AuditListQuery>): void {
    setSearchParams(writeQuery({ ...query, ...next, page: 1 }));
  }

  if (audit.isLoading) return <Spinner label="Loading the audit trail…" />;

  if (audit.isError) {
    return <ErrorState message={apiErrorMessage(audit.error)} onRetry={() => void audit.refetch()} />;
  }

  return (
    <>
      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="flex min-w-[12rem] flex-1 flex-col gap-1 sm:flex-none">
          <label htmlFor="audit-search" className="text-xs font-medium text-text-secondary">
            Search
          </label>
          <input
            id="audit-search"
            type="search"
            value={query.q}
            onChange={(event) => apply({ q: event.target.value })}
            placeholder="Action, actor, entity or IP…"
            className={FIELD_CLASS}
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="audit-entity" className="text-xs font-medium text-text-secondary">
            Entity
          </label>
          <select
            id="audit-entity"
            value={query.entity}
            onChange={(event) => apply({ entity: event.target.value })}
            className={FIELD_CLASS}
          >
            <option value="">All entities</option>
            {facets.entities.map((entity) => (
              <option key={entity} value={entity}>
                {entity}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="audit-action" className="text-xs font-medium text-text-secondary">
            Action
          </label>
          <select
            id="audit-action"
            value={query.action}
            onChange={(event) => apply({ action: event.target.value })}
            className={FIELD_CLASS}
          >
            <option value="">All actions</option>
            {facets.actions.map((action) => (
              <option key={action} value={action}>
                {action}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="audit-actor" className="text-xs font-medium text-text-secondary">
            Actor
          </label>
          <select
            id="audit-actor"
            value={query.actor}
            onChange={(event) => apply({ actor: event.target.value })}
            className={FIELD_CLASS}
          >
            <option value="">Anyone</option>
            {facets.actors.map((actor) => (
              <option key={actor} value={actor}>
                {actor}
              </option>
            ))}
          </select>
        </div>
      </div>

      {entries.length === 0 ? (
        <EmptyState
          title="No audit entries"
          description="Nothing has been recorded yet. Every administrative action appears here."
        />
      ) : page.rows.length === 0 ? (
        <EmptyState
          title="No entries match these filters"
          description="Try a different action, entity or actor."
        />
      ) : (
        <>
          {/* A timeline rather than a dense table: the audit trail is read chronologically, and
              grouping each entry's identity, target and diff summary in one block is what makes a
              long list scannable. */}
          <ol className="space-y-2">
            {page.rows.map((entry) => {
              const changes = auditChanges(entry);
              return (
                <li key={entry.id}>
                  <button
                    type="button"
                    onClick={() => setInspecting(entry)}
                    className="flex w-full flex-wrap items-start gap-3 rounded-md border border-border p-3 text-left hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  >
                    <span
                      aria-hidden
                      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                        isSecurityEvent(entry.action) ? "bg-danger" : "bg-border"
                      }`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <span className="font-medium text-text-primary">
                          {humanizeAction(entry.action)}
                        </span>
                        <span className="rounded-full border border-border px-2 py-0.5 text-xs text-text-secondary">
                          {actionEntity(entry.action)}
                        </span>
                        {isSecurityEvent(entry.action) ? <SecurityChip /> : null}
                      </span>
                      <span className="mt-1 block text-xs text-text-secondary">
                        {entry.actor ?? entry.actor_type}
                        {entry.entity_type
                          ? ` · ${entry.entity_type}${entry.entity_id !== null ? ` #${entry.entity_id}` : ""}`
                          : ""}
                        {entry.ip_address ? ` · ${entry.ip_address}` : ""}
                      </span>
                      {changes.length > 0 ? (
                        <span className="mt-1 block truncate text-xs text-text-disabled">
                          {changes.map((change) => change.field).join(", ")}
                        </span>
                      ) : null}
                    </span>
                    <span className="shrink-0 text-xs text-text-secondary">
                      {entry.created_at ? formatDateTime(entry.created_at) : UNKNOWN}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>

          <AdminPagination
            page={page.page}
            totalPages={page.totalPages}
            total={page.total}
            noun="entry"
            nounPlural="entries"
            filtered={isFiltered}
            onGoTo={(next) => setSearchParams(writeQuery({ ...query, page: next }))}
            truncatedTo={{ loaded: entries.length, available: total }}
          />
        </>
      )}

      {inspecting ? (
        <AuditDetailDialog entry={inspecting} onClose={() => setInspecting(null)} />
      ) : null}
    </>
  );
}
