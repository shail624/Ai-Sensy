import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge } from "@/components/ui";
import { KycOperationsWorkspace } from "@/features/kyc";
import {
  DocumentCenter,
  ReactivationPipelineBoard,
  ReactivationReports,
  REACTIVATION_SECTIONS,
} from "@/features/reactivation";
import { useHasPermission } from "@/lib/auth";

const LEGACY_REACTIVATION_REDIRECTS: Record<string, string> = {
  "/reactivation/eligible": "/reactivation/pipeline?view=list",
  "/reactivation/bulk-eligibility": "/contacts?import=1",
  "/reactivation/interested": "/reactivation/pipeline?stage=lead_confirmed&view=list",
  "/reactivation/sim-orders": "/reactivation/pipeline?stage=sim_required&view=list",
  "/reactivation/activation": "/reactivation/pipeline?stage=activation_pending&view=list",
  "/reactivation/completed": "/reactivation/pipeline?stage=completed&view=list",
};

export function ReactivationPage(): JSX.Element {
  const location = useLocation();
  const canReadKyc = useHasPermission("kyc:read");
  const canReadDocuments = useHasPermission("documents:read");
  const canReadReports = useHasPermission("analytics:read");
  const visibleSections = REACTIVATION_SECTIONS.filter((section) => {
    if (section.phase !== "Connected") return false;
    if (section.key === "kyc") return canReadKyc;
    if (section.key === "documents") return canReadDocuments;
    if (section.key === "reports") return canReadReports;
    return true;
  });
  const active = visibleSections.find((section) => location.pathname.startsWith(section.path));

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          { label: "Reactivation", to: "/reactivation/pipeline" },
          ...(active ? [{ label: active.label }] : []),
        ]}
      />
      <PageHeader
        eyebrow="Vi Reactivation operations"
        title={active?.label ?? "Reactivation CRM"}
        description={
          active?.description ??
          "One persisted operator workspace over the existing Reactivation, Task, KYC, Document, Audit, and Customer Timeline authorities."
        }
        meta={
          <>
            <Badge tone="success" dot>
              Connected
            </Badge>
            <span>Real tenant-scoped records · permission-aware actions · immutable evidence</span>
          </>
        }
      />

      <nav
        aria-label="Reactivation sections"
        className="mb-5 flex gap-1 overflow-x-auto rounded-surface border border-border bg-surface p-1.5 shadow-sm"
      >
        {visibleSections.map((section) => {
          const Icon = section.icon;
          return (
            <NavLink
              key={section.key}
              to={section.path}
              className={({ isActive }) =>
                `flex min-h-10 shrink-0 items-center gap-2 rounded-control px-3 text-sm font-semibold transition-colors ${
                  isActive
                    ? "bg-accent text-accent-fg shadow-sm"
                    : "text-text-secondary hover:bg-hover hover:text-text-primary"
                }`
              }
            >
              <Icon aria-hidden className="h-4 w-4" />
              {section.shortLabel}
            </NavLink>
          );
        })}
      </nav>

      <Outlet />
    </PageContainer>
  );
}

export function ReactivationOverview(): JSX.Element {
  return <Navigate to="/reactivation/pipeline" replace />;
}

export function ReactivationWorkspace(): JSX.Element {
  const location = useLocation();
  const redirect = LEGACY_REACTIVATION_REDIRECTS[location.pathname];
  if (redirect) return <Navigate to={redirect} replace />;

  const section = REACTIVATION_SECTIONS.find((item) => location.pathname.startsWith(item.path));
  if (section?.key === "pipeline") return <ReactivationPipelineBoard />;
  if (section?.key === "kyc") return <KycOperationsWorkspace />;
  if (section?.key === "documents") return <DocumentCenter />;
  if (section?.key === "reports") return <ReactivationReports />;

  return <Navigate to="/reactivation/pipeline" replace />;
}
