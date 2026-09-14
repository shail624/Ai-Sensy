import { Badge, EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useTeamWorkload } from "@/features/analytics/api";

interface TeamWorkloadTableProps {
  enabled: boolean;
}

function count(value: number): string {
  return value.toLocaleString();
}

export function TeamWorkloadTable({ enabled }: TeamWorkloadTableProps): JSX.Element | null {
  const query = useTeamWorkload(enabled);
  if (!enabled) return null;
  if (query.isLoading) return <Spinner label="Loading current team workload…" />;
  if (query.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(query.error)}
        onRetry={() => void query.refetch()}
      />
    );
  }

  const snapshot = query.data;
  if (!snapshot || snapshot.data.length === 0) {
    return (
      <EmptyState
        compact
        title="No team workload"
        description="No active teammate or assigned pending work is available in this workspace."
      />
    );
  }

  const asOf = snapshot.as_of.replace("T", " ").slice(0, 19);
  return (
    <div className="space-y-3">
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ["Unresolved chats", snapshot.totals.unresolved_conversations],
          ["Unread chats", snapshot.totals.unread_conversations],
          ["Open tasks", snapshot.totals.open_tasks],
          ["Overdue tasks", snapshot.totals.overdue_tasks],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-border bg-surface-2 px-3 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-text-disabled">{label}</p>
            <p className="mt-1 text-xl font-bold tabular-nums text-text-primary">{count(Number(value))}</p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-xl border border-border">
        <table className="w-full min-w-[760px] text-left text-xs">
          <thead className="border-b border-border bg-surface-2 text-[10px] font-semibold uppercase tracking-wide text-text-disabled">
            <tr>
              <th className="px-4 py-2.5">Teammate</th>
              <th className="px-3 py-2.5 text-right">Unresolved</th>
              <th className="px-3 py-2.5 text-right">Unread</th>
              <th className="px-3 py-2.5 text-right">Open tasks</th>
              <th className="px-3 py-2.5 text-right">Overdue</th>
              <th className="px-3 py-2.5 text-right">Due today</th>
              <th className="px-4 py-2.5">State</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {snapshot.data.map((row) => (
              <tr key={row.user_id ?? "unassigned"} className="hover:bg-hover">
                <td className="px-4 py-3 font-semibold text-text-primary">{row.user_name}</td>
                <td className="px-3 py-3 text-right tabular-nums text-text-secondary">{count(row.unresolved_conversations)}</td>
                <td className="px-3 py-3 text-right tabular-nums text-text-secondary">{count(row.unread_conversations)}</td>
                <td className="px-3 py-3 text-right tabular-nums text-text-secondary">{count(row.open_tasks)}</td>
                <td className="px-3 py-3 text-right tabular-nums text-text-secondary">{count(row.overdue_tasks)}</td>
                <td className="px-3 py-3 text-right tabular-nums text-text-secondary">{count(row.due_today_tasks)}</td>
                <td className="px-4 py-3">
                  {row.user_id === null ? (
                    <Badge tone="danger">Assign now</Badge>
                  ) : row.is_active === false ? (
                    <Badge tone="danger">Inactive owner</Badge>
                  ) : row.attention_required ? (
                    <Badge tone="warning">Attention</Badge>
                  ) : (
                    <Badge tone="success">Current</Badge>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-[11px] text-text-disabled">
        Snapshot {asOf} UTC · “Due today” uses {snapshot.timezone}. Pending stock is not added across dates.
      </p>
    </div>
  );
}
