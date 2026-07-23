import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import {
  apiErrorMessage,
  useDeletePipeline,
  useHasPermission,
  useUpdatePipeline,
} from "@/features/pipelines/api";
import { PipelineFormDialog } from "@/features/pipelines/PipelineFormDialog";
import type { Pipeline } from "@/features/pipelines/types";
import { canBecomeDefault, isDeletable } from "@/features/pipelines/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Props {
  pipeline: Pipeline;
  /** Every pipeline name, for the rename dialog's uniqueness check. */
  existingNames: string[];
  currentDefault?: string;
  /** After an archive the detail page must leave; the list just refreshes in place. */
  onDeleted?: () => void;
  compact?: boolean;
}

/**
 * The pipeline action set (Doc 07 §19.2), gated twice over.
 *
 * **By permission** — `contacts:write` for every change, `contacts:read` to see it at all. Leads
 * deliberately reuse the CRM permissions rather than defining their own.
 *
 * **By state** — the default pipeline cannot be archived (the server answers 409) and cannot be
 * made default again, so neither control is offered on it.
 */
export function PipelineActions({
  pipeline,
  existingNames,
  currentDefault,
  onDeleted,
  compact = false,
}: Props): JSX.Element {
  const navigate = useNavigate();
  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const canWrite = useHasPermission("contacts:write");
  const update = useUpdatePipeline();
  const remove = useDeletePipeline();

  const pending = update.isPending || remove.isPending;

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        {compact ? (
          <button
            type="button"
            className={ACTION_CLASS}
            onClick={() => navigate(`/pipelines/${pipeline.id}`)}
          >
            Open
          </button>
        ) : null}

        {canWrite ? (
          <button type="button" className={ACTION_CLASS} onClick={() => setEditing(true)}>
            Rename
          </button>
        ) : null}

        {canWrite && canBecomeDefault(pipeline) ? (
          <button
            type="button"
            className={ACTION_CLASS}
            disabled={pending}
            onClick={() =>
              update.mutate({ pipelineId: pipeline.id, body: { is_default: true } })
            }
          >
            Make default
          </button>
        ) : null}

        {canWrite && isDeletable(pipeline) ? (
          <button
            type="button"
            className={`${ACTION_CLASS} text-danger`}
            disabled={pending}
            onClick={() => setDeleting(true)}
          >
            Archive
          </button>
        ) : null}
      </div>

      {canWrite && !isDeletable(pipeline) && !compact ? (
        <p className="text-xs text-text-disabled">
          The default pipeline cannot be archived — move the default elsewhere first.
        </p>
      ) : null}

      {update.error ? <p className="text-xs text-danger">{apiErrorMessage(update.error)}</p> : null}
      {remove.error && !deleting ? (
        <p className="text-xs text-danger">{apiErrorMessage(remove.error)}</p>
      ) : null}

      {editing ? (
        <PipelineFormDialog
          pipeline={pipeline}
          existingNames={existingNames}
          currentDefault={currentDefault}
          onClose={() => setEditing(false)}
        />
      ) : null}

      {deleting ? (
        <ConfirmDialog
          title={`Archive "${pipeline.name}"?`}
          body={`The pipeline and its ${pipeline.stages.length} stage${
            pipeline.stages.length === 1 ? "" : "s"
          } are archived together. Nothing here can restore them, and any lead recorded against a stage keeps its history.`}
          confirmLabel="Archive pipeline"
          destructive
          pending={remove.isPending}
          error={remove.error}
          onClose={() => setDeleting(false)}
          onConfirm={() =>
            remove.mutate(pipeline.id, {
              onSuccess: () => {
                setDeleting(false);
                onDeleted?.();
              },
            })
          }
        />
      ) : null}
    </div>
  );
}
