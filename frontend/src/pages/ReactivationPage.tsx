import { ArrowRight, ChevronDown, Layers3, LockKeyhole, Radar } from "lucide-react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge, Card } from "@/components/ui";
import {
  DocumentCenter,
  ReactivationMissionControl,
  ReactivationPipelineBoard,
  ReactivationReports,
  REACTIVATION_FOUNDATION_SECTIONS,
  REACTIVATION_LIVE_SECTIONS,
  REACTIVATION_SECTIONS,
} from "@/features/reactivation";
import { KycOperationsWorkspace } from "@/features/kyc";

export function ReactivationPage(): JSX.Element {
  const location = useLocation();
  const isOverview = location.pathname === "/reactivation" || location.pathname === "/reactivation/";
  const active = REACTIVATION_SECTIONS.find((section) => location.pathname.startsWith(section.path));
  const title = isOverview ? "Mission Control" : active?.label ?? "Reactivation";
  const description = isOverview
    ? "Prioritize customer work by urgency, SLA, release date, evidence, ownership and the next required action."
    : active?.description ?? "One governed workspace for the complete reactivation journey.";
  const status = isOverview || active?.operationalGroup === "live" ? "Live operations" : "Capability boundary";

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          { label: "Reactivation", to: "/reactivation" },
          ...(isOverview || !active ? [] : [{ label: active.label }]),
        ]}
      />
      <PageHeader
        eyebrow="Vi Reactivation operations"
        title={title}
        description={description}
        meta={
          <>
            <Badge tone={status === "Live operations" ? "success" : "neutral"} dot>{status}</Badge>
            <span>Persisted tenant-scoped data · source permissions remain authoritative</span>
          </>
        }
        actions={
          !isOverview ? (
            <Link
              to="/reactivation"
              className="inline-flex min-h-9 items-center gap-2 rounded-control border border-border bg-surface px-3 text-xs font-semibold text-text-primary transition-colors hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <Radar aria-hidden className="h-4 w-4" /> Mission Control
            </Link>
          ) : undefined
        }
      />

      <div className="mb-5 space-y-2">
        <nav
          aria-label="Live Reactivation workspaces"
          className="flex gap-1.5 overflow-x-auto rounded-surface border border-border bg-surface p-1.5 shadow-sm"
        >
          <NavLink
            end
            to="/reactivation"
            className={({ isActive }) => navClass(isActive)}
          >
            <Radar aria-hidden className="h-4 w-4" /> Mission Control
          </NavLink>
          {REACTIVATION_LIVE_SECTIONS.map((section) => {
            const Icon = section.icon;
            return (
              <NavLink key={section.key} to={section.path} className={({ isActive }) => navClass(isActive)}>
                <Icon aria-hidden className="h-4 w-4" />{section.shortLabel}
              </NavLink>
            );
          })}
        </nav>

        <details className="group rounded-control border border-dashed border-border bg-surface-2">
          <summary className="flex min-h-10 cursor-pointer list-none items-center justify-between gap-3 px-3 text-xs font-semibold text-text-secondary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus [&::-webkit-details-marker]:hidden">
            <span className="flex items-center gap-2"><Layers3 aria-hidden className="h-4 w-4" /> Foundation capability routes</span>
            <span className="flex items-center gap-2"><Badge tone="neutral">Not active queues</Badge><ChevronDown aria-hidden className="h-4 w-4 transition-transform group-open:rotate-180" /></span>
          </summary>
          <div className="grid gap-2 border-t border-border p-2 sm:grid-cols-2 xl:grid-cols-3">
            {REACTIVATION_FOUNDATION_SECTIONS.map((section) => {
              const Icon = section.icon;
              return (
                <Link
                  key={section.key}
                  to={section.path}
                  className="flex min-h-12 items-center gap-3 rounded-control border border-border bg-surface px-3 py-2 text-left transition-colors hover:border-border-strong hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                >
                  <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-control bg-surface-2 text-text-secondary"><Icon aria-hidden className="h-4 w-4" /></span>
                  <span className="min-w-0"><span className="block text-xs font-semibold text-text-primary">{section.label}</span><span className="mt-0.5 block truncate text-[11px] text-text-secondary">Uses an existing source workflow</span></span>
                </Link>
              );
            })}
          </div>
        </details>
      </div>

      <Outlet />
    </PageContainer>
  );
}

function navClass(isActive: boolean): string {
  return `flex min-h-10 shrink-0 items-center gap-2 rounded-control px-3 text-sm font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
    isActive ? "bg-accent text-accent-fg shadow-sm" : "text-text-secondary hover:bg-hover hover:text-text-primary"
  }`;
}

export function ReactivationOverview(): JSX.Element {
  return <ReactivationMissionControl />;
}

export function ReactivationWorkspace(): JSX.Element {
  const location = useLocation();
  const section = REACTIVATION_SECTIONS.find((item) => location.pathname.startsWith(item.path));
  if (section?.key === "pipeline") return <ReactivationPipelineBoard />;
  if (section?.key === "kyc") return <KycOperationsWorkspace />;
  if (section?.key === "documents") return <DocumentCenter />;
  if (section?.key === "reports") return <ReactivationReports />;
  if (!section) return <ReactivationMissionControl />;

  const actionByKey: Record<string, { label: string; path: string; authority: string }> = {
    eligible: { label: "Open prioritized pipeline", path: "/reactivation/pipeline?view=attention", authority: "Eligibility evidence on persisted cases" },
    bulk: { label: "Open contact import", path: "/contacts?import=1", authority: "Governed contact import" },
    interested: { label: "Open active pipeline", path: "/reactivation/pipeline?view=all", authority: "Persisted Reactivation cases" },
    sim: { label: "Open SIM risk queue", path: "/reactivation/pipeline?view=sim", authority: "SIM Required case status and Tasks" },
    activation: { label: "Open activation risk queue", path: "/reactivation/pipeline?view=activation", authority: "Activation Pending case status" },
    completed: { label: "Open completed cases", path: "/reactivation/pipeline?status=completed&view=all", authority: "Persisted completed cases" },
  };
  const action = actionByKey[section.key];
  const Icon = section.icon;

  return (
    <Card className="overflow-hidden" padding={false}>
      <div className="grid lg:grid-cols-[minmax(0,1fr)_21rem]">
        <div className="p-5 sm:p-7">
          <div className="flex items-start gap-3">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-control bg-surface-2 text-text-secondary"><Icon aria-hidden className="h-5 w-5" /></span>
            <div>
              <Badge tone="neutral"><LockKeyhole aria-hidden className="mr-1 h-3.5 w-3.5" />Foundation boundary</Badge>
              <h2 className="mt-3 text-lg font-semibold text-text-primary">{section.label} is not a separate operating authority</h2>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-secondary">{section.description}</p>
            </div>
          </div>

          <div className="mt-6 rounded-surface border border-border bg-surface-2 p-4">
            <h3 className="text-sm font-semibold text-text-primary">Use the connected source instead</h3>
            <dl className="mt-3 grid gap-3 text-xs sm:grid-cols-2">
              <div><dt className="text-text-disabled">Current authority</dt><dd className="mt-1 font-semibold text-text-primary">{action?.authority ?? "Mission Control and source records"}</dd></div>
              <div><dt className="text-text-disabled">Data boundary</dt><dd className="mt-1 font-semibold text-text-primary">No duplicate record, KPI or workflow is created here</dd></div>
            </dl>
            <div className="mt-4 flex flex-wrap gap-2">
              {action ? <BoundaryLink to={action.path} label={action.label} /> : null}
              <BoundaryLink to="/reactivation" label="Return to Mission Control" secondary />
            </div>
          </div>
        </div>
        <aside className="border-t border-border bg-surface-2 p-5 lg:border-l lg:border-t-0">
          <h3 className="text-sm font-semibold text-text-primary">Why this is separated</h3>
          <ul className="mt-3 space-y-3 text-xs leading-relaxed text-text-secondary">
            <li>Operators should not mistake a future capability for a live queue.</li>
            <li>Existing permissions, APIs, audit evidence and business transitions remain authoritative.</li>
            <li>A dedicated product is added only after an approved server-owned contract exists.</li>
          </ul>
        </aside>
      </div>
    </Card>
  );
}

function BoundaryLink({ to, label, secondary = false }: { to: string; label: string; secondary?: boolean }): JSX.Element {
  return (
    <Link
      to={to}
      className={`inline-flex min-h-9 items-center gap-2 rounded-control border px-3 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${secondary ? "border-border bg-surface text-text-primary hover:bg-hover" : "border-accent bg-accent text-accent-fg hover:bg-accent-hover"}`}
    >
      {label}<ArrowRight aria-hidden className="h-3.5 w-3.5" />
    </Link>
  );
}
