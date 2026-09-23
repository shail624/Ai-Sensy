import { lazy, Suspense } from "react";
import { FileText, MessageSquareText, Send, Users } from "lucide-react";
import { Link } from "react-router-dom";

import { Skeleton } from "@/components/ui";
import { useAccountSummary } from "@/features/channels/api";
import { useCampaigns } from "@/features/campaigns";
import { useContactSearch } from "@/features/contacts";
import { AccountStatusCard } from "@/features/dashboard/AccountStatusCard";
import { DASH_CARD } from "@/features/dashboard/dashboardStyles";
import { SetupChecklist, buildSetupSteps } from "@/features/dashboard/SetupChecklist";
import { WabaProfileCard } from "@/features/dashboard/WabaProfileCard";
import { useTemplates } from "@/features/templates/api";
import { isSendable } from "@/features/templates/types";
import { useHasPermission } from "@/lib/auth";

const OperationalDashboard = lazy(() =>
  import("@/features/dashboard/OperationalDashboard").then((module) => ({
    default: module.OperationalDashboard,
  })),
);

function DashboardLoading(): JSX.Element {
  return (
    <div aria-label="Loading operational dashboard" className="space-y-4" role="status">
      <Skeleton className="h-12 w-full" />
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, index) => (
          <Skeleton key={index} className="h-24 w-full" />
        ))}
      </div>
      <span className="sr-only">Loading live operational intelligence</span>
    </div>
  );
}

const QUICK_ACTIONS = [
  { label: "Live Chat", description: "Reply to waiting customers", path: "/inbox", icon: MessageSquareText, permission: "inbox:read" },
  { label: "New Campaign", description: "Broadcast an approved template", path: "/campaigns/new", icon: Send, permission: "campaigns:write" },
  { label: "Contacts", description: "Find or add a customer", path: "/contacts", icon: Users, permission: "contacts:read" },
  { label: "Templates", description: "Create or check message templates", path: "/templates", icon: FileText, permission: "templates:read" },
] as const;

function QuickActions(): JSX.Element | null {
  const allowed = {
    "inbox:read": useHasPermission("inbox:read"),
    "campaigns:write": useHasPermission("campaigns:write"),
    "contacts:read": useHasPermission("contacts:read"),
    "templates:read": useHasPermission("templates:read"),
  };
  const actions = QUICK_ACTIONS.filter((action) => allowed[action.permission]);
  if (actions.length === 0) return null;
  return (
    <section aria-labelledby="quick-actions-title" className={`${DASH_CARD} px-5 py-2.5`}>
      <h2 id="quick-actions-title" className="py-1.5 text-sm font-normal leading-[19px] text-text-primary">Quick actions</h2>
      <ul className="grid grid-cols-2 gap-2 pb-2.5 pt-1">
        {actions.map((action) => {
          const Icon = action.icon;
          return (
            <li key={action.path}>
              <Link
                to={action.path}
                className="group flex h-full flex-col gap-1.5 rounded-lg border border-[#f0f0f0] p-3 transition-[border-color,box-shadow,transform] duration-200 hover:-translate-y-px hover:border-transparent hover:shadow-card focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:border-border"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-[#ebf5f3] text-[var(--color-nav-bg)] dark:bg-accent-soft dark:text-accent">
                  <Icon aria-hidden className="h-4 w-4" />
                </span>
                <span className="text-sm font-semibold text-text-primary">{action.label}</span>
                <span className="text-xs leading-4 text-[#6e6e6e] dark:text-text-secondary">{action.description}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

export function DashboardPage(): JSX.Element {
  const canWaba = useHasPermission("waba:read");
  const canManageWaba = useHasPermission("waba:manage");
  const canTemplates = useHasPermission("templates:read");
  const canContacts = useHasPermission("contacts:read");
  const canCampaigns = useHasPermission("campaigns:read");

  const account = useAccountSummary(canWaba);
  const templates = useTemplates(canTemplates);
  const campaigns = useCampaigns(canCampaigns);
  const contacts = useContactSearch({ rules: [], cursor: null, limit: 1 }, canContacts);

  const steps = buildSetupSteps({
    whatsappConnected: account.summary?.status === "live",
    templateApproved: (templates.data ?? []).some(isSendable),
    hasContacts: (contacts.data?.data.length ?? 0) > 0,
    hasCampaign: (campaigns.data?.length ?? 0) > 0,
  });

  return (
    <div className="mx-auto w-full max-w-[1264px] px-4 py-6 sm:px-4">
      <h1 className="sr-only">Dashboard</h1>
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_387px]">
        <div className="min-w-0 space-y-4">
          {canWaba ? (
            <AccountStatusCard summary={account.summary} loading={account.isLoading} canManage={canManageWaba} />
          ) : null}
          <SetupChecklist steps={steps} />
        </div>
        <div className="min-w-0 space-y-4">
          {canWaba ? <WabaProfileCard summary={account.summary} loading={account.isLoading} canManage={canManageWaba} /> : null}
          <QuickActions />
        </div>
      </div>

      <section aria-labelledby="todays-work-title" className="mt-6">
        <h2 id="todays-work-title" className="mb-3 text-lg font-normal leading-[21px] text-text-primary">Today&apos;s work</h2>
        <Suspense fallback={<DashboardLoading />}>
          <OperationalDashboard />
        </Suspense>
      </section>
    </div>
  );
}
