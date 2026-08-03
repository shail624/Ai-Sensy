import { lazy, Suspense } from "react";
import { MessageSquareText, Send } from "lucide-react";
import { Link } from "react-router-dom";

import { PageContainer, PageHeader } from "@/components/layout";
import { Skeleton } from "@/components/ui";
import { useAuth, useHasPermission } from "@/lib/auth";

const OperationalDashboard = lazy(() =>
  import("@/features/dashboard/OperationalDashboard").then((module) => ({
    default: module.OperationalDashboard,
  })),
);

const SECONDARY_ACTION =
  "inline-flex h-9 max-md:h-10 items-center justify-center gap-2 rounded-control border border-border bg-surface px-4 text-sm font-semibold text-text-primary shadow-sm transition-[background-color,border-color,color,box-shadow] hover:border-border-strong hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";
const PRIMARY_ACTION =
  "inline-flex h-9 max-md:h-10 items-center justify-center gap-2 rounded-control border border-transparent bg-accent px-4 text-sm font-semibold text-accent-fg shadow-sm transition-[background-color,border-color,color,box-shadow] hover:bg-accent-strong focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

function DashboardLoading(): JSX.Element {
  return (
    <div aria-label="Loading operational dashboard" className="space-y-5" role="status">
      <Skeleton className="h-12 w-full" />
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {Array.from({ length: 9 }, (_, index) => (
          <Skeleton key={index} className="h-28 w-full" />
        ))}
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(20rem,0.7fr)]">
        <Skeleton className="h-96 w-full" />
        <Skeleton className="h-96 w-full" />
      </div>
      <span className="sr-only">Loading live operational intelligence</span>
    </div>
  );
}

export function DashboardPage(): JSX.Element {
  const { user } = useAuth();
  const canInbox = useHasPermission("inbox:read");
  const canCreateCampaign = useHasPermission("campaigns:write");
  const firstName = user?.full_name.trim().split(/\s+/)[0] ?? "there";

  return (
    <PageContainer>
      <PageHeader
        eyebrow="Daily operations"
        title="Operations desk"
        description={`${greeting()}, ${firstName}. Start with blocked customers, breached service work, waiting conversations and today’s KPI changes.`}
        meta={
          <>
            <span>Real authorized tenant data</span>
            <span>Decision-first operational view</span>
          </>
        }
        actions={
          <>
            {canInbox ? (
              <Link to="/inbox" className={SECONDARY_ACTION}>
                <MessageSquareText aria-hidden className="h-4 w-4" />
                Live chat
              </Link>
            ) : null}
            {canCreateCampaign ? (
              <Link to="/campaigns/new" className={PRIMARY_ACTION}>
                <Send aria-hidden className="h-4 w-4" />
                New campaign
              </Link>
            ) : null}
          </>
        }
      />
      <Suspense fallback={<DashboardLoading />}>
        <OperationalDashboard />
      </Suspense>
    </PageContainer>
  );
}
