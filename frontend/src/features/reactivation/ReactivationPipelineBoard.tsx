import { Clock3, Filter, History, Search, SlidersHorizontal, Users } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Card, EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, usePipelines } from "@/features/pipelines/api";
import { orderedStages } from "@/features/pipelines/types";

export const REACTIVATION_STAGE_BLUEPRINT = ["Lead", "Eligibility Check", "Interested", "Documents Received", "Verification", "KYC Approved", "SIM Ordered", "Activation Pending", "Activated", "Completed"];

/**
 * Enterprise Kanban shell over the real pipeline configuration.
 *
 * Lead-card placement is deliberately absent: the current contract can configure/reorder stages,
 * but it cannot list or move a conversation lead. Rendering fake cards would create false state.
 */
export function ReactivationPipelineBoard(): JSX.Element {
  const pipelines = usePipelines();
  const [query, setQuery] = useState("");
  const [pipelineId, setPipelineId] = useState("");
  const selected = useMemo(() => {
    const rows = pipelines.data ?? [];
    return rows.find((row) => row.id === pipelineId) ?? rows.find((row) => row.is_default) ?? rows[0];
  }, [pipelineId, pipelines.data]);
  const stages = selected ? orderedStages(selected).filter((stage) => stage.name.toLowerCase().includes(query.toLowerCase())) : [];

  if (pipelines.isLoading) return <Spinner label="Loading customer pipeline…" />;
  if (pipelines.isError) return <ErrorState message={apiErrorMessage(pipelines.error)} onRetry={() => void pipelines.refetch()} />;

  return (
    <div className="space-y-4">
      <Card className="p-4" padding={false}><div className="flex items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-text-primary">Recommended reactivation blueprint</h2><p className="mt-1 text-xs text-text-secondary">Reference only. Operators decide whether to configure these stages in the real pipeline.</p></div><Badge tone="info">10 stages</Badge></div><div className="mt-3 flex gap-2 overflow-x-auto pb-1">{REACTIVATION_STAGE_BLUEPRINT.map((stage,index) => <div key={stage} className="flex shrink-0 items-center gap-2"><span className="rounded-xl border border-border bg-surface-2 px-3 py-2 text-xs font-semibold text-text-primary">{index+1}. {stage}</span>{index<REACTIVATION_STAGE_BLUEPRINT.length-1 ? <span aria-hidden className="text-text-disabled">→</span> : null}</div>)}</div></Card>
      <Card className="sticky top-0 z-10 flex flex-wrap items-end gap-3 p-4" padding={false}>
        <div className="min-w-[12rem] flex-1">
          <label htmlFor="pipeline-board" className="text-xs font-semibold text-text-secondary">Pipeline</label>
          <select id="pipeline-board" value={selected?.id ?? ""} onChange={(event) => setPipelineId(event.target.value)} className="mt-1 h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary">
            {(pipelines.data ?? []).map((pipeline) => <option key={pipeline.id} value={pipeline.id}>{pipeline.name}{pipeline.is_default ? " · Default" : ""}</option>)}
          </select>
        </div>
        <div className="min-w-[14rem] flex-[2]">
          <label htmlFor="pipeline-search" className="text-xs font-semibold text-text-secondary">Search stages</label>
          <div className="relative mt-1"><Search aria-hidden className="absolute left-3 top-3 h-4 w-4 text-text-disabled" /><input id="pipeline-search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a stage" className="h-10 w-full rounded-xl border border-border bg-surface pl-9 pr-3 text-sm text-text-primary" /></div>
        </div>
        {selected ? <Link to={`/pipelines/${selected.id}`} className="inline-flex min-h-10 items-center gap-2 rounded-xl border border-border px-3 text-sm font-semibold text-text-primary hover:bg-hover"><SlidersHorizontal aria-hidden className="h-4 w-4" />Configure stages</Link> : null}
      </Card>

      <div className="flex gap-3 overflow-x-auto pb-3" aria-label="Reactivation pipeline stages">
        {stages.map((stage) => (
          <section key={stage.id} className="w-[18rem] shrink-0 rounded-2xl border border-border bg-surface-2 p-3" aria-label={stage.name}>
            <header className="mb-3 flex items-center justify-between gap-2"><h2 className="text-sm font-semibold text-text-primary">{stage.name}</h2><Badge tone={stage.is_terminal ? "success" : "neutral"}>0 verified</Badge></header>
            <EmptyState compact title="No verified cards" description="Lead placement requires the additive conversation-lead transition contract." />
          </section>
        ))}
      </div>

      {selected && stages.length === 0 ? <EmptyState title="No matching stages" description="Clear the search or configure this pipeline." /> : null}
      {!selected ? <EmptyState title="No pipeline configured" description="Create a pipeline before organizing the reactivation journey." /> : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {[
          [Users, "Assignments", "Conversation assignment remains the owner source of truth."],
          [Clock3, "SLA and follow-up", "Due work remains in the production task queue."],
          [History, "Activity and history", "Customer and task events remain append-only."],
          [Filter, "Saved views", "Pipeline-card views activate with the lead-list contract."],
        ].map(([Icon, title, description]) => { const Glyph = Icon as typeof Users; return <Card key={title as string} className="p-4" padding={false}><Glyph aria-hidden className="h-5 w-5 text-accent" /><h3 className="mt-3 text-sm font-semibold text-text-primary">{title as string}</h3><p className="mt-1 text-xs leading-relaxed text-text-secondary">{description as string}</p></Card>; })}
      </div>
    </div>
  );
}
