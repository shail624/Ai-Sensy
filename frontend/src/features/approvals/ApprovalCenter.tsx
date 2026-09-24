import { Link } from "react-router-dom";

import {
  Badge,
  Button,
  Card,
  CardHeader,
  EmptyState,
  ErrorState,
  Skeleton,
} from "@/components/ui";
import {
  apiErrorMessage,
  useApprove,
  useHasPermission,
  usePendingApprovals,
} from "@/features/approvals/api";
import { SOURCE_LABELS, SOURCE_PERMISSION, type PendingApproval } from "@/features/approvals/types";
import { formatAge } from "@/lib/format";

/**
 * Everything waiting on somebody's approval, in one place.
 *
 * `MODULE_STATUS` recorded CORE-08 as *"Skipped: Not required by product owner"*, refusing a
 * generic approval **framework** — a second authority deciding who may act. This is not that, and
 * the distinction is the whole design: nothing here decides anything. Each item is approved
 * through the endpoint its own module already owns, under the permission that module already
 * checks, and this screen only answers the question none of them could: *what is waiting on me?*
 *
 * Until now that answer lived in two separate workspaces, and something waiting in the one nobody
 * opened today waited another day.
 */
export function ApprovalCenter(): JSX.Element {
  const canKyc = useHasPermission("kyc:read");
  const canActivation = useHasPermission("activation:read");
  const approvals = usePendingApprovals(canKyc, canActivation);
  const approve = useApprove();

  const items = approvals.data ?? [];

  if (!canKyc && !canActivation) {
    return (
      <EmptyState
        title="No approvals to show"
        description="Your role cannot see KYC or activations. Ask your admin."
      />
    );
  }

  return (
    <Card padding={false} className="overflow-hidden">
      <CardHeader
        className="border-b border-border px-4 py-4 sm:px-5"
        title="Waiting on you"
        description="KYC checks and activations waiting for your OK."
      />

      <div className="p-4 sm:px-5">
        {approvals.isPending ? (
          <Skeleton className="h-32 rounded-xl" />
        ) : approvals.isError ? (
          <ErrorState
            message={apiErrorMessage(approvals.error)}
            onRetry={() => void approvals.refetch()}
          />
        ) : items.length === 0 ? (
          <EmptyState
            title="Nothing waiting"
            description="Nothing needs your approval right now."
          />
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <ApprovalRow
                key={`${item.source}-${item.id}`}
                item={item}
                pending={approve.isPending}
                onApprove={() => approve.mutate(item)}
              />
            ))}
          </ul>
        )}

        {approve.isError ? (
          <p role="alert" className="mt-3 text-sm text-danger">
            {apiErrorMessage(approve.error)}
          </p>
        ) : null}
      </div>
    </Card>
  );
}

function ApprovalRow({
  item,
  pending,
  onApprove,
}: {
  item: PendingApproval;
  pending: boolean;
  onApprove: () => void;
}): JSX.Element {
  // The approve permission, not the read one: somebody may legitimately see the queue and not be
  // the person who signs it off, and a button they cannot use is worse than no button.
  const canApprove = useHasPermission(SOURCE_PERMISSION[item.source]);

  return (
    <li className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-surface-subtle p-3">
      <Badge tone="info">{SOURCE_LABELS[item.source]}</Badge>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-text-primary">{item.label}</p>
        <p className="mt-0.5 text-xs text-text-secondary">{item.detail}</p>
      </div>
      <p className="text-xs text-text-disabled">Waiting {formatAge(item.waitingSince)}</p>
      {item.contactId ? (
        <Link
          to={`/contacts/${item.contactId}`}
          className="text-xs font-semibold text-accent hover:underline"
        >
          Open customer
        </Link>
      ) : null}
      {canApprove ? (
        <Button size="sm" disabled={pending} onClick={onApprove}>
          Approve
        </Button>
      ) : null}
    </li>
  );
}
