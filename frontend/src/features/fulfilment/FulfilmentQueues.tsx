import { useState } from "react";

import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Input,
  Skeleton,
} from "@/components/ui";
import {
  apiErrorMessage,
  useActivationRecords,
  useHasPermission,
  useSimOrders,
  useTransitionActivation,
  useTransitionSimOrder,
} from "@/features/fulfilment/api";
import {
  ACTIVATION_SETTLED,
  ACTIVATION_STATUS_LABELS,
  ACTIVATION_STATUSES,
  ACTIVATION_TONES,
  SIM_SETTLED,
  SIM_STATUS_LABELS,
  SIM_STATUSES,
  SIM_TONES,
  type ActivationRecord,
  type ActivationStatus,
  type SimOrder,
  type SimStatus,
} from "@/features/fulfilment/types";
import { formatDateTime } from "@/lib/format";

/**
 * What a SIM order can become next.
 *
 * The API accepts any status and enforces the real rules; this only decides which buttons are
 * worth drawing, so an operator is not offered "requested" on something already delivered. A
 * refusal from the server is still the authority — this list never widens what is allowed, only
 * narrows what is offered.
 */
const SIM_NEXT: Record<SimStatus, SimStatus[]> = {
  requested: ["approved", "cancelled"],
  approved: ["assigned", "cancelled"],
  assigned: ["dispatched", "failed", "cancelled"],
  dispatched: ["delivered", "failed"],
  delivered: [],
  failed: ["assigned"],
  cancelled: [],
};

const ACTIVATION_NEXT: Record<ActivationStatus, ActivationStatus[]> = {
  pending: ["verification", "rejected"],
  verification: ["ready", "rejected"],
  ready: ["approved", "rejected"],
  approved: ["completed", "rejected"],
  completed: [],
  rejected: [],
};

function matches(haystack: (string | null | undefined)[], needle: string): boolean {
  if (!needle) return true;
  const lower = needle.toLocaleLowerCase();
  return haystack.some((value) => (value ?? "").toLocaleLowerCase().includes(lower));
}

/**
 * The two fulfilment queues — SIM delivery and activation — on one operations page.
 *
 * Both lifecycles have had complete APIs since CORE-02 and no screen at all: an operator could
 * only reach an order through the one reactivation case it belongs to, so "what is waiting on us
 * today" had no answer anywhere. That is the question a queue exists to answer, and it is the
 * reason these are boards by status rather than flat lists.
 *
 * Settled work is folded away by default. A queue that keeps showing completed orders stops being
 * a list of what to do and becomes a list of what happened.
 */
export function FulfilmentQueues(): JSX.Element {
  const [search, setSearch] = useState("");
  const [showSettled, setShowSettled] = useState(false);
  const canReadSim = useHasPermission("sim:read");
  const canReadActivation = useHasPermission("activation:read");

  return (
    <div className="space-y-5">
      <Card padding={false} className="overflow-hidden">
        <CardHeader
          className="border-b border-border px-4 py-4 sm:px-5"
          title="Fulfilment queues"
          description="SIM delivery and activation, across every reactivation case. Settled work is hidden until you ask for it."
          action={
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowSettled((current) => !current)}
            >
              {showSettled ? "Hide settled" : "Show settled"}
            </Button>
          }
        />
        <div className="p-4 sm:px-5">
          <Input
            aria-label="Search by serial, address or area"
            placeholder="Search by serial, address or area"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
      </Card>

      {canReadSim ? <SimQueue search={search} showSettled={showSettled} /> : null}
      {canReadActivation ? <ActivationQueue search={search} showSettled={showSettled} /> : null}

      {!canReadSim && !canReadActivation ? (
        <EmptyState
          title="No fulfilment access"
          description="You need SIM or activation read permission to see these queues."
        />
      ) : null}
    </div>
  );
}

function SimQueue({ search, showSettled }: { search: string; showSettled: boolean }): JSX.Element {
  const orders = useSimOrders();
  const transition = useTransitionSimOrder();
  const canManage = useHasPermission("sim:write");

  const visible = (orders.data ?? []).filter(
    (order) =>
      (showSettled || !SIM_SETTLED.includes(order.status as SimStatus)) &&
      matches([order.sim_serial, order.delivery_address, order.service_area], search),
  );
  const columns = SIM_STATUSES.filter(
    (status) => showSettled || !SIM_SETTLED.includes(status),
  );

  return (
    <Card padding={false} className="overflow-hidden">
      <CardHeader
        className="border-b border-border px-4 py-4 sm:px-5"
        title="SIM delivery"
        description="Every order that has not reached the customer yet."
      />
      <div className="p-4 sm:px-5">
        {orders.isPending ? (
          <Skeleton className="h-32 rounded-xl" />
        ) : orders.isError ? (
          <ErrorState message={apiErrorMessage(orders.error)} onRetry={() => void orders.refetch()} />
        ) : visible.length === 0 ? (
          <EmptyState
            title="Nothing waiting"
            description={
              search
                ? "No order matches that search."
                : "Every SIM order has reached the customer or been closed."
            }
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {columns.map((status) => {
              const rows = visible.filter((order) => order.status === status);
              if (rows.length === 0) return null;
              return (
                <section key={status} aria-labelledby={`sim-${status}`}>
                  <h3 id={`sim-${status}`} className="mb-2 flex items-center gap-2 text-sm font-semibold text-text-primary">
                    <Badge tone={SIM_TONES[status]}>{SIM_STATUS_LABELS[status]}</Badge>
                    <span className="text-text-secondary">{rows.length}</span>
                  </h3>
                  <div className="space-y-2">
                    {rows.map((order) => (
                      <SimCard
                        key={order.id}
                        order={order}
                        canManage={canManage}
                        pending={transition.isPending}
                        onMove={(to) => transition.mutate({ order, to })}
                      />
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        )}
        {transition.isError ? (
          <p role="alert" className="mt-3 text-sm text-danger">
            {apiErrorMessage(transition.error)}
          </p>
        ) : null}
      </div>
    </Card>
  );
}

function SimCard({
  order,
  canManage,
  pending,
  onMove,
}: {
  order: SimOrder;
  canManage: boolean;
  pending: boolean;
  onMove: (to: SimStatus) => void;
}): JSX.Element {
  const next = SIM_NEXT[order.status as SimStatus] ?? [];
  return (
    <div className="rounded-xl border border-border bg-surface-subtle p-3">
      <p className="text-sm font-medium text-text-primary">
        {order.sim_serial ?? "No serial yet"}
      </p>
      <p className="mt-0.5 text-xs text-text-secondary">
        {order.service_area ?? "No service area"}
      </p>
      {order.delivery_address ? (
        <p className="mt-1 line-clamp-2 text-xs text-text-disabled">{order.delivery_address}</p>
      ) : null}
      {order.failure_reason ? (
        <p className="mt-1 text-xs text-danger">{order.failure_reason}</p>
      ) : null}
      <p className="mt-1 text-[11px] text-text-disabled">
        Updated {formatDateTime(order.updated_at)}
      </p>
      {canManage && next.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {next.map((status) => (
            <Button
              key={status}
              variant="secondary"
              size="sm"
              disabled={pending}
              onClick={() => onMove(status)}
            >
              {SIM_STATUS_LABELS[status]}
            </Button>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function ActivationQueue({
  search,
  showSettled,
}: {
  search: string;
  showSettled: boolean;
}): JSX.Element {
  const records = useActivationRecords();
  const transition = useTransitionActivation();
  const canManage = useHasPermission("activation:write");

  const visible = (records.data ?? []).filter(
    (record) =>
      (showSettled || !ACTIVATION_SETTLED.includes(record.status as ActivationStatus)) &&
      matches([record.approval_reference, record.rejection_reason], search),
  );
  const columns = ACTIVATION_STATUSES.filter(
    (status) => showSettled || !ACTIVATION_SETTLED.includes(status),
  );

  return (
    <Card padding={false} className="overflow-hidden">
      <CardHeader
        className="border-b border-border px-4 py-4 sm:px-5"
        title="Activation"
        description="Records waiting on verification, approval or completion."
      />
      <div className="p-4 sm:px-5">
        {records.isPending ? (
          <Skeleton className="h-32 rounded-xl" />
        ) : records.isError ? (
          <ErrorState
            message={apiErrorMessage(records.error)}
            onRetry={() => void records.refetch()}
          />
        ) : visible.length === 0 ? (
          <EmptyState
            title="Nothing waiting"
            description={
              search
                ? "No activation matches that search."
                : "Every activation has completed or been closed."
            }
          />
        ) : (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {columns.map((status) => {
              const rows = visible.filter((record) => record.status === status);
              if (rows.length === 0) return null;
              return (
                <section key={status} aria-labelledby={`act-${status}`}>
                  <h3 id={`act-${status}`} className="mb-2 flex items-center gap-2 text-sm font-semibold text-text-primary">
                    <Badge tone={ACTIVATION_TONES[status]}>
                      {ACTIVATION_STATUS_LABELS[status]}
                    </Badge>
                    <span className="text-text-secondary">{rows.length}</span>
                  </h3>
                  <div className="space-y-2">
                    {rows.map((record) => (
                      <ActivationCard
                        key={record.id}
                        record={record}
                        canManage={canManage}
                        pending={transition.isPending}
                        onMove={(to) => transition.mutate({ record, to })}
                      />
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        )}
        {transition.isError ? (
          <p role="alert" className="mt-3 text-sm text-danger">
            {apiErrorMessage(transition.error)}
          </p>
        ) : null}
      </div>
    </Card>
  );
}

function ActivationCard({
  record,
  canManage,
  pending,
  onMove,
}: {
  record: ActivationRecord;
  canManage: boolean;
  pending: boolean;
  onMove: (to: ActivationStatus) => void;
}): JSX.Element {
  const next = ACTIVATION_NEXT[record.status as ActivationStatus] ?? [];
  return (
    <div className="rounded-xl border border-border bg-surface-subtle p-3">
      <p className="text-sm font-medium text-text-primary">
        {record.approval_reference ?? "No approval reference"}
      </p>
      {record.rejection_reason ? (
        <p className="mt-1 text-xs text-danger">{record.rejection_reason}</p>
      ) : null}
      <p className="mt-1 text-[11px] text-text-disabled">
        Updated {formatDateTime(record.updated_at)}
      </p>
      {canManage && next.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1">
          {next.map((status) => (
            <Button
              key={status}
              variant="secondary"
              size="sm"
              disabled={pending}
              onClick={() => onMove(status)}
            >
              {ACTIVATION_STATUS_LABELS[status]}
            </Button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
