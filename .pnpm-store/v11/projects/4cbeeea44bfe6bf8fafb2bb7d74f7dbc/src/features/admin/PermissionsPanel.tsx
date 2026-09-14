import { KeyRound } from "lucide-react";

import { Badge, Card, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import { apiErrorMessage, usePermissions } from "@/features/admin/api";
import type { Permission } from "@/features/admin/types";

export function PermissionsPanel(): JSX.Element {
  const query = usePermissions();
  if (query.isLoading) return <div className="grid gap-4 md:grid-cols-2"><Skeleton className="h-44 rounded-2xl" /><Skeleton className="h-44 rounded-2xl" /></div>;
  if (query.isError) return <ErrorState message={apiErrorMessage(query.error)} onRetry={() => void query.refetch()} />;
  if (!query.data?.length) return <EmptyState title="No permissions registered" description="The permission catalog is empty." />;

  const groups = query.data.reduce<Map<string, Permission[]>>((result, permission) => {
    result.set(permission.resource, [...(result.get(permission.resource) ?? []), permission]);
    return result;
  }, new Map());
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      {[...groups.entries()].map(([resource, permissions]) => (
        <Card key={resource}>
          <div className="mb-4 flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent"><KeyRound aria-hidden className="h-5 w-5" /></span><div><h2 className="font-bold capitalize text-text-primary">{resource}</h2><p className="text-xs text-text-secondary">{permissions.length} registered capabilities</p></div></div>
          <div className="space-y-2">
            {permissions.map((permission) => <div key={permission.code} className="rounded-xl border border-border bg-surface-subtle p-3"><div className="flex items-center justify-between gap-2"><code className="text-xs font-semibold text-text-primary">{permission.code}</code><Badge>{permission.action}</Badge></div>{permission.description ? <p className="mt-1.5 text-xs leading-relaxed text-text-secondary">{permission.description}</p> : null}</div>)}
          </div>
        </Card>
      ))}
    </div>
  );
}
