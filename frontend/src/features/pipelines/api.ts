import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  Pipeline,
  PipelineCreateRequest,
  PipelineUpdateRequest,
  Stage,
  StageCreateRequest,
  StageUpdateRequest,
} from "@/features/pipelines/types";

// Shared error helper, re-exported for this feature's components (as the other features do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const pipelineKeys = {
  all: ["pipelines"] as const,
  list: () => ["pipelines", "list"] as const,
  detail: (id: string) => ["pipelines", "detail", id] as const,
};

/**
 * Every pipeline in the organization, each with its stages already ordered.
 *
 * `GET /lead-pipelines` takes **no parameters at all** and returns the complete list with stages
 * nested — the relationship is `selectin`-loaded and ordered by `position`, so one request holds
 * everything this module needs. Search, filtering and sorting therefore run in the client over a
 * genuinely complete set.
 */
export function usePipelines() {
  return useQuery({
    queryKey: pipelineKeys.list(),
    queryFn: async (): Promise<Pipeline[]> => unwrap(await api.GET("/api/v1/lead-pipelines")),
  });
}

export function usePipeline(pipelineId: string, enabled = true) {
  return useQuery({
    queryKey: pipelineKeys.detail(pipelineId),
    queryFn: async (): Promise<Pipeline> =>
      unwrap(
        await api.GET("/api/v1/lead-pipelines/{pipeline_id}", {
          params: { path: { pipeline_id: pipelineId } },
        }),
      ),
    enabled: enabled && Boolean(pipelineId),
  });
}

/**
 * Every pipeline and stage write is audited, and a stage change alters its pipeline, so the whole
 * feature is invalidated together along with the audit trail.
 */
function usePipelineMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: pipelineKeys.all });
      void queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

/** Pipeline names are unique within the organization — a duplicate answers 409. */
export function useCreatePipeline() {
  return usePipelineMutation(
    async (body: PipelineCreateRequest): Promise<Pipeline> =>
      unwrap(await api.POST("/api/v1/lead-pipelines", { body })),
  );
}

/**
 * Rename a pipeline, or move the default flag to it.
 *
 * Setting `is_default` clears it from whichever pipeline held it, so the flag **moves**. The server
 * acts only on a truthy value, which means the default can be moved but never cleared — an
 * organization always has one.
 */
export function useUpdatePipeline() {
  return usePipelineMutation(
    async ({
      pipelineId,
      body,
    }: {
      pipelineId: string;
      body: PipelineUpdateRequest;
    }): Promise<Pipeline> =>
      unwrap(
        await api.PATCH("/api/v1/lead-pipelines/{pipeline_id}", {
          params: { path: { pipeline_id: pipelineId } },
          body,
        }),
      ),
  );
}

/**
 * Archive a pipeline and, with it, every stage it owns.
 *
 * A soft delete rather than a destructive one, and refused for the default (409). There is no
 * un-archive endpoint, so it is one-way from here.
 */
export function useDeletePipeline() {
  return usePipelineMutation(async (pipelineId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/lead-pipelines/{pipeline_id}", {
      params: { path: { pipeline_id: pipelineId } },
    });
    if (error !== undefined) throw error;
  });
}

/**
 * Add a stage.
 *
 * Names are unique within the pipeline (409). A stage is appended and then moved if `position` is
 * supplied, so passing one inserts rather than appends.
 */
export function useAddStage() {
  return usePipelineMutation(
    async ({
      pipelineId,
      body,
    }: {
      pipelineId: string;
      body: StageCreateRequest;
    }): Promise<Stage> =>
      unwrap(
        await api.POST("/api/v1/lead-pipelines/{pipeline_id}/stages", {
          params: { path: { pipeline_id: pipelineId } },
          body,
        }),
      ),
  );
}

/**
 * Rename, re-flag or **reorder** a stage.
 *
 * Reordering is a first-class server operation: supplying `position` moves the stage and
 * re-indexes its siblings densely, so one PATCH expresses a whole move and no second request is
 * needed to fix up the neighbours.
 */
export function useUpdateStage() {
  return usePipelineMutation(
    async ({ stageId, body }: { stageId: string; body: StageUpdateRequest }): Promise<Stage> =>
      unwrap(
        await api.PATCH("/api/v1/lead-stages/{stage_id}", {
          params: { path: { stage_id: stageId } },
          body,
        }),
      ),
  );
}

/** Archive a stage. Soft, and with no un-archive endpoint to reverse it. */
export function useDeleteStage() {
  return usePipelineMutation(async (stageId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/lead-stages/{stage_id}", {
      params: { path: { stage_id: stageId } },
    });
    if (error !== undefined) throw error;
  });
}
