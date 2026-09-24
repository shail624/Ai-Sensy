import { ArrowRight, BarChart3, CheckCircle2, Clock3, CopyCheck, FileUp, RefreshCw, ScanSearch, ShieldCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, Button, Card, EmptyState } from "@/components/ui";
import { ReachabilityPanel } from "@/features/scan/ReachabilityPanel";

const STEPS = ["Upload numbers", "Batch manager", "Scan queue", "Processing", "Active", "Inactive", "Business accounts", "Statistics", "Export", "Create segment", "Launch campaign"];

/** Separate scan-product integration seam. It never calls or masquerades as Meta Cloud API. */
export function ScanWorkspace(): JSX.Element {
  return <div className="space-y-5">
    <Card className="overflow-hidden" padding={false}><div className="grid lg:grid-cols-[1.3fr_0.7fr]"><div className="p-6 sm:p-8"><div className="flex items-center gap-3"><span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft text-accent"><ScanSearch aria-hidden className="h-6 w-6" /></span><div><Badge tone="info">Independent integration</Badge><h2 className="mt-1 text-lg font-bold text-text-primary">WhatsApp number scan workflow</h2></div></div><p className="mt-4 max-w-3xl text-sm leading-relaxed text-text-secondary">Number scanning will be a separate tool with its own lists and reports. It is kept apart from your official WhatsApp number and campaigns.</p><div className="mt-5 flex flex-wrap gap-2"><Link to="/contacts?import=1"><Button leftIcon={<FileUp className="h-4 w-4" />}>Import numbers into CRM</Button></Link><Link to="/segments"><Button variant="secondary" rightIcon={<ArrowRight className="h-4 w-4" />}>Open segments</Button></Link></div></div><div className="border-t border-border bg-surface-2 p-6 lg:border-l lg:border-t-0"><div className="flex items-start gap-3 text-sm"><ShieldCheck aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-success" /><div><p className="font-semibold text-text-primary">Architecture boundary enforced</p><p className="mt-1 leading-relaxed text-text-secondary">No unofficial scanner, credentials, batch, queue task, network request, or inferred WhatsApp status exists in this repository.</p></div></div></div></div></Card>

    <section aria-labelledby="scan-flow-title"><div className="mb-3 flex items-center justify-between gap-3"><div><h2 id="scan-flow-title" className="text-base font-semibold text-text-primary">Batch journey</h2><p className="mt-1 text-sm text-text-secondary">End-to-end product flow, ready for an independently approved adapter contract.</p></div><Badge tone="neutral">No batches</Badge></div><div role="group" aria-label="Batch journey steps" tabIndex={0} className="flex gap-2 overflow-x-auto pb-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">{STEPS.map((step,index) => <div key={step} className="flex shrink-0 items-center gap-2"><span className="inline-flex min-h-10 items-center rounded-xl border border-border bg-surface px-3 text-xs font-semibold text-text-primary"><span className="mr-2 text-text-disabled">{index+1}</span>{step}</span>{index<STEPS.length-1 ? <ArrowRight aria-hidden className="h-4 w-4 text-text-disabled" /> : null}</div>)}</div></section>

    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4"><Capability icon={CopyCheck} title="Duplicate detection" text="Will normalize and compare within the scan batch before queueing." /><Capability icon={RefreshCw} title="Retry and comparison" text="Will preserve attempts and compare batches through a scan-owned retry ledger." /><Capability icon={Clock3} title="Progress and history" text="Will expose real queued, processing, complete, and failed counts from its worker." /><Capability icon={BarChart3} title="Analytics and export" text="Will publish scan dimensions before segment or campaign hand-off is enabled." /></div>

    {/* SCAN-01. The direct batch scan above still has no contract; this is the part that can be
        answered compliantly today, from delivery receipts the platform already holds. */}
    <ReachabilityPanel />

    <Card className="p-6" padding={false}><EmptyState icon={<ScanSearch className="h-7 w-7" />} title="Checking numbers you never messaged is not available" description="The results above come from campaigns you already sent. WhatsApp&rsquo;s official API cannot check a list of numbers in advance, and unofficial checking tools are not allowed in this app." action={<div className="flex flex-wrap justify-center gap-2"><Button disabled title="Not available yet">Upload scan batch</Button><Button variant="secondary" disabled title="Nothing to export yet">Export results</Button></div>} /></Card>
  </div>;
}

function Capability({ icon: Icon, title, text }: { icon: typeof CheckCircle2; title: string; text: string }): JSX.Element {
  return <Card className="p-4" padding={false}><Icon aria-hidden className="h-5 w-5 text-accent" /><h3 className="mt-3 text-sm font-semibold text-text-primary">{title}</h3><p className="mt-1 text-xs leading-relaxed text-text-secondary">{text}</p></Card>;
}
