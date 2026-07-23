import { Modal } from "@/components/ui";
import { SecurityChip } from "@/features/admin/AdminBadges";
import { auditChanges } from "@/features/admin/selectors";
import type { AuditEntry } from "@/features/admin/types";
import { humanizeAction, isSecurityEvent } from "@/features/admin/types";
import { formatDateTime, UNKNOWN } from "@/lib/format";

function render(value: unknown): string {
  if (value === undefined) return "—";
  if (value === null) return "null";
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

/**
 * One audit entry in full (Doc 05 B11.10).
 *
 * The `before`/`after` snapshots are free-form objects, so rather than dumping both this shows the
 * **fields that actually differ** — which is what an investigator is reading the entry for. The raw
 * snapshots stay available underneath, because a diff that hides an unexpected key would defeat
 * the point of an immutable trail.
 */
export function AuditDetailDialog({
  entry,
  onClose,
}: {
  entry: AuditEntry;
  onClose: () => void;
}): JSX.Element {
  const changes = auditChanges(entry);

  return (
    <Modal title={humanizeAction(entry.action)} onClose={onClose}>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <code className="rounded border border-border bg-surface-2 px-2 py-0.5 font-mono text-xs text-text-primary">
            {entry.action}
          </code>
          {isSecurityEvent(entry.action) ? <SecurityChip /> : null}
        </div>

        <dl className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs">
          <Row label="When">{formatDateTime(entry.created_at)}</Row>
          <Row label="Actor">{entry.actor ?? `${entry.actor_type} (no user)`}</Row>
          <Row label="Actor type">{entry.actor_type}</Row>
          <Row label="Entity">
            {entry.entity_type
              ? `${entry.entity_type}${entry.entity_id !== null ? ` #${entry.entity_id}` : ""}`
              : UNKNOWN}
          </Row>
          <Row label="IP address">{entry.ip_address ?? UNKNOWN}</Row>
        </dl>

        <div>
          <p className="text-xs font-medium text-text-secondary">Changes</p>
          {changes.length === 0 ? (
            <p className="mt-1 text-sm text-text-disabled">
              This action recorded no field-level change.
            </p>
          ) : (
            <div className="mt-1 overflow-x-auto rounded-md border border-border">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-border bg-surface-2 text-text-secondary">
                  <tr>
                    <th scope="col" className="px-2 py-1.5">Field</th>
                    <th scope="col" className="px-2 py-1.5">Before</th>
                    <th scope="col" className="px-2 py-1.5">After</th>
                  </tr>
                </thead>
                <tbody>
                  {changes.map((change) => (
                    <tr key={change.field} className="border-b border-border last:border-0">
                      <td className="px-2 py-1.5 font-mono text-text-primary">{change.field}</td>
                      <td className="break-all px-2 py-1.5 text-text-secondary">
                        {render(change.before)}
                      </td>
                      <td className="break-all px-2 py-1.5 text-text-primary">
                        {render(change.after)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {entry.metadata && Object.keys(entry.metadata).length > 0 ? (
          <details>
            <summary className="cursor-pointer text-xs text-text-secondary">Metadata</summary>
            <pre className="mt-1 overflow-x-auto rounded-md border border-border bg-surface-2 p-2 text-xs text-text-primary">
              {JSON.stringify(entry.metadata, null, 2)}
            </pre>
          </details>
        ) : null}

        <details>
          <summary className="cursor-pointer text-xs text-text-secondary">Raw snapshots</summary>
          <pre className="mt-1 overflow-x-auto rounded-md border border-border bg-surface-2 p-2 text-xs text-text-primary">
            {JSON.stringify({ before: entry.before, after: entry.after }, null, 2)}
          </pre>
        </details>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover"
          >
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }): JSX.Element {
  return (
    <div className="flex justify-between gap-3 py-0.5">
      <dt className="shrink-0 text-text-secondary">{label}</dt>
      <dd className="min-w-0 break-all text-right text-text-primary">{children}</dd>
    </div>
  );
}
