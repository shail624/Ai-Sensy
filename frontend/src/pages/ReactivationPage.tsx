import { ArrowRight, CheckCircle2, DatabaseZap, ShieldCheck, Sparkles } from "lucide-react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge, Button, Card, CardHeader, EmptyState } from "@/components/ui";
import { AiFoundationPanel } from "@/features/ai";
import { DocumentCenter, ReactivationPipelineBoard, ReactivationReports, REACTIVATION_SECTIONS } from "@/features/reactivation";
import { KycOperationsWorkspace } from "@/features/kyc";

export function ReactivationPage(): JSX.Element {
  const location = useLocation();
  const active = REACTIVATION_SECTIONS.find((section) => location.pathname.startsWith(section.path));
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Reactivation", to: "/reactivation" }, ...(active ? [{ label: active.label }] : [])]} />
      <PageHeader
        eyebrow="Vi customer journey"
        title={active?.label ?? "Reactivation"}
        description={active?.description ?? "One governed workspace for the complete reactivation journey, built over the production CRM and explicit domain integration boundaries."}
        meta={<><Badge tone={active?.phase === "Connected" ? "success" : "info"} dot>{active?.phase ?? "Phase 3 workspace"}</Badge><span>Verified data only · no inferred customer state</span></>}
      />

      <nav aria-label="Reactivation sections" className="mb-6 flex gap-2 overflow-x-auto rounded-2xl border border-border bg-surface p-2 shadow-sm">
        {REACTIVATION_SECTIONS.map((section) => {
          const Icon = section.icon;
          return <NavLink key={section.key} to={section.path} className={({isActive}) => `flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-3 text-sm font-medium transition-colors ${isActive ? "bg-accent text-accent-fg shadow-sm" : "text-text-secondary hover:bg-hover hover:text-text-primary"}`}><Icon aria-hidden className="h-4 w-4" />{section.shortLabel}</NavLink>;
        })}
      </nav>

      <Outlet />
    </PageContainer>
  );
}

export function ReactivationOverview(): JSX.Element {
  return <div className="space-y-6">
    <Card className="overflow-hidden" padding={false}>
      <div className="grid lg:grid-cols-[1.2fr_0.8fr]">
        <div className="p-6 sm:p-8"><CardHeader title="One governed customer journey" description="The live pipeline uses persisted reactivation cases while later operational workspaces remain milestone-gated." icon={<Sparkles aria-hidden className="h-5 w-5" />} /><div className="mt-6 grid gap-3 sm:grid-cols-2">{REACTIVATION_SECTIONS.map((section) => {const Icon=section.icon; return <Link key={section.key} to={section.path} className="group flex items-center gap-3 rounded-xl border border-border bg-surface-2 p-3 transition-colors hover:border-accent"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface text-accent"><Icon aria-hidden className="h-4 w-4" /></span><span className="min-w-0 flex-1"><span className="block text-sm font-medium text-text-primary">{section.label}</span><span className="block text-xs text-text-secondary">{section.phase}</span></span><ArrowRight aria-hidden className="h-4 w-4 text-text-disabled group-hover:text-accent" /></Link>;})}</div></div>
        <div className="border-t border-border bg-[linear-gradient(145deg,var(--color-accent-soft),var(--color-bg-surface-2))] p-6 lg:border-l lg:border-t-0"><h2 className="text-sm font-semibold text-text-primary">Phase 3 operating model</h2><ul className="mt-4 space-y-3">{[[CheckCircle2,"Persisted cases, tasks, documents and CRM evidence are reused"],[ShieldCheck,"Permissions, audit and server transition boundaries remain authoritative"],[DatabaseZap,"Later KYC, fulfilment and activation workspaces remain milestone-gated"]].map(([Icon,label]) => {const Glyph=Icon as typeof CheckCircle2; return <li key={label as string} className="flex gap-3 text-sm leading-relaxed text-text-secondary"><Glyph aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-success" />{label as string}</li>;})}</ul></div>
      </div>
    </Card>
  </div>;
}

export function ReactivationWorkspace(): JSX.Element {
  const location = useLocation();
  const section = REACTIVATION_SECTIONS.find((item) => location.pathname.startsWith(item.path));
  if (section?.key === "pipeline") return <ReactivationPipelineBoard />;
  if (section?.key === "kyc") return <KycOperationsWorkspace />;
  if (section?.key === "documents") return <DocumentCenter />;
  if (section?.key === "reports") return <ReactivationReports />;

  const actionByKey: Record<string, { label: string; path: string }> = {
    eligible: { label: "Build an eligibility segment", path: "/segments/new" },
    bulk: { label: "Open contact import", path: "/contacts?import=1" },
    interested: { label: "Open customer CRM", path: "/contacts" },
    documents: { label: "Open document library", path: "/media?type=document" },
    sim: { label: "Open fulfilment tasks", path: "/tasks" },
    activation: { label: "Open customer pipeline", path: "/pipelines" },
    completed: { label: "Open customer CRM", path: "/contacts" },
  };
  const action = section ? actionByKey[section.key] : undefined;
  const Icon = section?.icon ?? Sparkles;
  return <div className="space-y-5"><Card className="overflow-hidden" padding={false}><div className="grid min-h-[360px] lg:grid-cols-[1fr_22rem]"><div className="p-6 sm:p-8"><Badge tone={section?.phase === "Connected" ? "success" : "info"} dot>{section?.phase ?? "Foundation"}</Badge><h2 className="mt-4 text-xl font-bold text-text-primary">{section?.label ?? "Reactivation workspace"}</h2><p className="mt-2 max-w-2xl text-sm leading-relaxed text-text-secondary">{section?.description}</p><div className="mt-6 rounded-2xl border border-border bg-surface-2 p-5"><h3 className="text-sm font-semibold text-text-primary">Production capability</h3><p className="mt-2 text-sm leading-relaxed text-text-secondary">Operators continue through the existing CRM, task, segment, campaign, media, and audit systems. Dedicated eligibility, KYC, SIM, activation, and completion records remain unavailable until additive contracts are approved.</p>{action ? <Link to={action.path} className="mt-5 inline-block"><Button rightIcon={<ArrowRight className="h-4 w-4" />}>{action.label}</Button></Link> : null}</div></div><div className="flex items-center justify-center border-t border-border bg-[radial-gradient(circle_at_top,var(--color-accent-soft),var(--color-bg-surface-2))] p-6 lg:border-l lg:border-t-0"><EmptyState icon={<Icon className="h-7 w-7" />} title="Ready for governed data" description="Search, filters, bulk actions, history, and SLA views activate when this domain has a server-owned record." /></div></div></Card>{section?.key === "kyc" ? <StatusJourney title="KYC review model" statuses={["Pending", "Submitted", "Verified", "Rejected", "Approved"]} /> : null}{section?.key === "sim" ? <StatusJourney title="SIM lifecycle model" statuses={["Ordered", "Packed", "Dispatched", "Delivered", "Activated", "Completed"]} /> : null}{section?.key === "kyc" ? <AiFoundationPanel capabilities={["summary", "document"]} context="governed customer documents; analysis remains provider- and reviewer-gated" /> : null}</div>;
}

function StatusJourney({ title, statuses }: { title: string; statuses: string[] }): JSX.Element {
  return <Card className="p-4" padding={false}><div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-text-primary">{title}</h2><p className="mt-1 text-xs text-text-secondary">Reference state model only; reviewer, notes, tracking, approval, and audit require a dedicated record.</p></div><Badge tone="neutral">Contract gated</Badge></div><div className="mt-3 flex gap-2 overflow-x-auto pb-1">{statuses.map((status,index) => <div key={status} className="flex shrink-0 items-center gap-2"><span className="rounded-xl border border-border bg-surface-2 px-3 py-2 text-xs font-semibold text-text-primary">{status}</span>{index<statuses.length-1 ? <ArrowRight aria-hidden className="h-4 w-4 text-text-disabled" /> : null}</div>)}</div></Card>;
}
