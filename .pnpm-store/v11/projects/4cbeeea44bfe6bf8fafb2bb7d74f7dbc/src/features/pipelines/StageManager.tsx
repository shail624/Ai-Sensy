import { useState } from "react";

import { EmptyState, ErrorState, Modal, Section } from "@/components/ui";
import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import {
  apiErrorMessage,
  useAddStage,
  useDeleteStage,
  useHasPermission,
  useUpdateStage,
} from "@/features/pipelines/api";
import { PositionChip, TerminalChip } from "@/features/pipelines/PipelineBadges";
import { validateName } from "@/features/pipelines/selectors";
import type { Pipeline, Stage } from "@/features/pipelines/types";
import { canMoveDown, canMoveUp, MAX_NAME_LENGTH, orderedStages } from "@/features/pipelines/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";
const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

/**
 * The stages of one pipeline: add, rename, re-flag, reorder and archive.
 *
 * **Reordering is a real server operation.** `PATCH /lead-stages/{id}` with a `position` moves the
 * stage and re-indexes its siblings densely, so a whole move is one request and the neighbours need
 * no follow-up. It is offered two ways over that same call — dragging a row, and move up/down
 * buttons — because drag-and-drop alone is unusable by keyboard and untestable in practice.
 */
export function StageManager({ pipeline }: { pipeline: Pipeline }): JSX.Element {
  const canWrite = useHasPermission("contacts:write");
  const stages = orderedStages(pipeline);

  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<Stage | null>(null);
  const [deleting, setDeleting] = useState<Stage | null>(null);
  const [dragging, setDragging] = useState<number | null>(null);
  const [dropTarget, setDropTarget] = useState<number | null>(null);

  const update = useUpdateStage();
  const remove = useDeleteStage();

  function move(stage: Stage, to: number): void {
    update.mutate({ stageId: stage.id, body: { position: to } });
  }

  function handleDrop(to: number): void {
    const from = dragging;
    setDragging(null);
    setDropTarget(null);
    if (from === null || from === to) return;
    const stage = stages[from];
    if (stage) move(stage, to);
  }

  return (
    <Section
      title="Stages"
      action={
        canWrite ? (
          <button type="button" onClick={() => setAdding(true)} className={ACTION_CLASS}>
            Add stage
          </button>
        ) : null
      }
    >
      {update.error ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(update.error)} />
        </div>
      ) : null}
      {remove.error && !deleting ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(remove.error)} />
        </div>
      ) : null}

      {stages.length === 0 ? (
        <EmptyState
          title="No stages"
          description={
            canWrite
              ? "A pipeline needs at least one stage before a lead can sit anywhere in it."
              : "This pipeline has no stages yet."
          }
        />
      ) : (
        <>
          <ol className="space-y-2">
            {stages.map((stage, index) => (
              <li
                key={stage.id}
                draggable={canWrite}
                onDragStart={() => setDragging(index)}
                onDragEnd={() => {
                  setDragging(null);
                  setDropTarget(null);
                }}
                onDragOver={(event) => {
                  if (dragging === null) return;
                  // Without this the drop never fires — the default is to reject.
                  event.preventDefault();
                  setDropTarget(index);
                }}
                onDrop={(event) => {
                  event.preventDefault();
                  handleDrop(index);
                }}
                className={`flex flex-wrap items-center gap-3 rounded-md border p-3 ${
                  dropTarget === index && dragging !== null && dragging !== index
                    ? "border-accent"
                    : "border-border"
                } ${dragging === index ? "opacity-50" : ""} ${canWrite ? "cursor-grab" : ""}`}
              >
                <PositionChip position={stage.position} />

                <div className="min-w-0 flex-1">
                  <p className="font-medium text-text-primary">{stage.name}</p>
                  {stage.is_terminal ? (
                    <div className="mt-1">
                      <TerminalChip />
                    </div>
                  ) : null}
                </div>

                {canWrite ? (
                  <div className="flex flex-wrap items-center gap-1">
                    <button
                      type="button"
                      className={ACTION_CLASS}
                      aria-label={`Move ${stage.name} up`}
                      disabled={!canMoveUp(stages, index) || update.isPending}
                      onClick={() => move(stage, index - 1)}
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      className={ACTION_CLASS}
                      aria-label={`Move ${stage.name} down`}
                      disabled={!canMoveDown(stages, index) || update.isPending}
                      onClick={() => move(stage, index + 1)}
                    >
                      ↓
                    </button>
                    <button type="button" className={ACTION_CLASS} onClick={() => setEditing(stage)}>
                      Edit
                    </button>
                    <button
                      type="button"
                      className={`${ACTION_CLASS} text-danger`}
                      disabled={remove.isPending}
                      onClick={() => setDeleting(stage)}
                    >
                      Archive
                    </button>
                  </div>
                ) : null}
              </li>
            ))}
          </ol>

          {canWrite ? (
            <p className="mt-3 text-xs text-text-disabled">
              Drag a stage to reorder it, or use the arrows. Either way the whole order is rewritten
              in one request.
            </p>
          ) : null}
        </>
      )}

      {adding ? (
        <StageDialog
          pipeline={pipeline}
          onClose={() => setAdding(false)}
        />
      ) : null}

      {editing ? (
        <StageDialog pipeline={pipeline} stage={editing} onClose={() => setEditing(null)} />
      ) : null}

      {deleting ? (
        <ConfirmDialog
          title={`Archive "${deleting.name}"?`}
          body="The stage is archived rather than destroyed, but there is no way to restore it from here. Leads recorded against it keep their history."
          confirmLabel="Archive stage"
          destructive
          pending={remove.isPending}
          error={remove.error}
          onClose={() => setDeleting(null)}
          onConfirm={() =>
            remove.mutate(deleting.id, { onSuccess: () => setDeleting(null) })
          }
        />
      ) : null}
    </Section>
  );
}

interface DialogProps {
  pipeline: Pipeline;
  /** Present → rename/re-flag that stage; absent → add one. */
  stage?: Stage;
  onClose: () => void;
}

/** Add or edit a stage. Position is set by reordering, not typed, so it is absent here. */
function StageDialog({ pipeline, stage, onClose }: DialogProps): JSX.Element {
  const editing = stage !== undefined;
  const [name, setName] = useState(stage?.name ?? "");
  const [terminal, setTerminal] = useState(stage?.is_terminal ?? false);
  const [showErrors, setShowErrors] = useState(false);

  const add = useAddStage();
  const update = useUpdateStage();
  const pending = add.isPending || update.isPending;
  const error = add.error ?? update.error;

  const problem = validateName(
    name,
    pipeline.stages.map((entry) => entry.name),
    { currentName: stage?.name },
  );

  function submit(): void {
    setShowErrors(true);
    if (problem) return;

    if (editing) {
      update.mutate(
        { stageId: stage.id, body: { name: name.trim(), is_terminal: terminal } },
        { onSuccess: onClose },
      );
      return;
    }
    add.mutate(
      { pipelineId: pipeline.id, body: { name: name.trim(), is_terminal: terminal } },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal title={editing ? `Edit "${stage.name}"` : "Add a stage"} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label htmlFor="stage-name" className={LABEL_CLASS}>
            Stage name
          </label>
          <input
            id="stage-name"
            value={name}
            maxLength={MAX_NAME_LENGTH}
            onChange={(event) => setName(event.target.value)}
            placeholder="Documents Received"
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            {name.length}/{MAX_NAME_LENGTH} · must be unique within this pipeline
          </p>
          {showErrors && problem ? <p className="text-xs text-danger">{problem}</p> : null}
        </div>

        <label className="flex items-start gap-2 text-sm text-text-secondary">
          <input
            type="checkbox"
            checked={terminal}
            onChange={(event) => setTerminal(event.target.checked)}
            className="mt-1"
          />
          This is a final stage — a lead that reaches it has finished.
        </label>

        {!editing ? (
          <p className="text-xs text-text-disabled">
            New stages are added at the end. Reorder them afterwards by dragging or with the arrows.
          </p>
        ) : null}

        {error ? <p className="text-sm text-danger">{apiErrorMessage(error)}</p> : null}

        <div className="flex justify-end gap-2 pt-1">
          <button
            type="button"
            onClick={onClose}
            disabled={pending}
            className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={pending}
            className="rounded-md bg-accent px-3 py-1 text-sm text-accent-fg disabled:opacity-50"
          >
            {pending ? "Saving…" : editing ? "Save stage" : "Add stage"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
