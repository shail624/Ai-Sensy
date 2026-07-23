import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, usePipeline, usePipelines } from "@/features/pipelines/api";
import { PipelineActions } from "@/features/pipelines/PipelineActions";
import { DefaultChip, StageCountChip } from "@/features/pipelines/PipelineBadges";
import { terminalStages } from "@/features/pipelines/selectors";
import { StageManager } from "@/features/pipelines/StageManager";
import type { Pipeline } from "@/features/pipelines/types";
import { orderedStages } from "@/features/pipelines/types";
import { formatCount, formatDateTime, UNKNOWN } from "@/lib/format";

/**
 * One pipeline in full — its record, the stages in order, and the controls to change either.
 */
export function PipelineDetail({ pipelineId }: { pipelineId: string }): JSX.Element {
  const navigate = useNavigate();
  const pipeline = usePipeline(pipelineId);
  // The whole list is one cheap request and is already cached by the list screen; it supplies the
  // sibling names the rename dialog needs for its uniqueness check.
  const pipelines = usePipelines();

  const names = useMemo(
    () => (pipelines.data ?? []).map((entry) => entry.name),
    [pipelines.data],
  );
  const currentDefault = (pipelines.data ?? []).find((entry) => entry.is_default)?.name;

  if (pipeline.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading pipeline…" />
      </PageContainer>
    );
  }

  if (pipeline.isError || !pipeline.data) {
    return (
      <PageContainer>
        <Breadcrumbs items={[{ label: "Pipelines", to: "/pipelines" }, { label: "Pipeline" }]} />
        <ErrorState
          message={apiErrorMessage(pipeline.error)}
          onRetry={() => void pipeline.refetch()}
        />
      </PageContainer>
    );
  }

  const data = pipeline.data;
  const stages = orderedStages(data);

  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Pipelines", to: "/pipelines" }, { label: data.name }]} />
      <PageHeader
        title={data.name}
        description={
          stages.length === 0
            ? "No stages yet — a lead cannot sit anywhere in this pipeline."
            : `${stages.length} stage${stages.length === 1 ? "" : "s"}, in order.`
        }
        actions={
          <PipelineActions
            pipeline={data}
            existingNames={names}
            currentDefault={currentDefault}
            onDeleted={() => navigate("/pipelines")}
          />
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {data.is_default ? <DefaultChip /> : null}
        <StageCountChip count={stages.length} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
        <StageManager pipeline={data} />
        <RecordSection pipeline={data} />
      </div>
    </PageContainer>
  );
}

function RecordSection({ pipeline }: { pipeline: Pipeline }): JSX.Element {
  const stages = orderedStages(pipeline);
  const finals = terminalStages(pipeline);

  return (
    <Section title="Record">
      {stages.length > 0 && finals.length === 0 ? (
        <p className="mb-3 rounded-md border border-warning px-3 py-2 text-sm text-warning">
          No stage is marked final, so a lead in this pipeline has nowhere to finish. Mark the last
          stage — or the outcomes — as final.
        </p>
      ) : null}

      <dl>
        <DefinitionRow label="Default pipeline">
          {pipeline.is_default ? "Yes — new leads land here" : "No"}
        </DefinitionRow>
        <DefinitionRow label="Stages">{formatCount(stages.length)}</DefinitionRow>
        <DefinitionRow label="Final stages">
          {finals.length === 0 ? UNKNOWN : finals.join(", ")}
        </DefinitionRow>
        <DefinitionRow label="Created">{formatDateTime(pipeline.created_at)}</DefinitionRow>
        <DefinitionRow label="Last updated">{formatDateTime(pipeline.updated_at)}</DefinitionRow>
        <DefinitionRow label="Pipeline id">
          <span className="break-all font-mono text-xs">{pipeline.id}</span>
        </DefinitionRow>
      </dl>

      <p className="mt-3 text-xs text-text-disabled">
        Pipelines and stages are configuration only. Moving a lead onto a stage happens per
        conversation in the Inbox, and the platform records no lead counts against a stage here.
      </p>
    </Section>
  );
}
