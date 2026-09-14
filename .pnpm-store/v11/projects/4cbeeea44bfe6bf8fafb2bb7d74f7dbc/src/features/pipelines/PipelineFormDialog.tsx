import { useState } from "react";

import { Modal } from "@/components/ui";
import {
  apiErrorMessage,
  useCreatePipeline,
  useUpdatePipeline,
} from "@/features/pipelines/api";
import { validateName } from "@/features/pipelines/selectors";
import type { Pipeline } from "@/features/pipelines/types";
import { MAX_NAME_LENGTH } from "@/features/pipelines/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

interface Props {
  /** Present → rename that pipeline; absent → create one. */
  pipeline?: Pipeline;
  /** Every pipeline name in the organization, for the uniqueness check. */
  existingNames: string[];
  /** The pipeline that currently holds the default, so the move can be described precisely. */
  currentDefault?: string;
  onClose: () => void;
  onCreated?: (pipeline: Pipeline) => void;
}

/**
 * Create or rename a pipeline.
 *
 * `is_default` is a **move, not a toggle**: setting it clears the flag from whichever pipeline held
 * it, and the server acts only on a truthy value — so it can never be cleared, only relocated. The
 * control is therefore offered as an action to take rather than a checkbox to untick, and the
 * pipeline that currently holds it is named.
 */
export function PipelineFormDialog({
  pipeline,
  existingNames,
  currentDefault,
  onClose,
  onCreated,
}: Props): JSX.Element {
  const editing = pipeline !== undefined;
  const [name, setName] = useState(pipeline?.name ?? "");
  const [makeDefault, setMakeDefault] = useState(false);
  const [showErrors, setShowErrors] = useState(false);

  const create = useCreatePipeline();
  const update = useUpdatePipeline();
  const pending = create.isPending || update.isPending;
  const error = create.error ?? update.error;

  const problem = validateName(name, existingNames, { currentName: pipeline?.name });
  const alreadyDefault = pipeline?.is_default ?? false;

  function submit(): void {
    setShowErrors(true);
    if (problem) return;

    if (editing) {
      update.mutate(
        {
          pipelineId: pipeline.id,
          // Only send the flag when it is being moved: sending `false` would be a no-op the server
          // ignores, and sending it needlessly would muddy the audit entry.
          body: { name: name.trim(), ...(makeDefault ? { is_default: true } : {}) },
        },
        { onSuccess: onClose },
      );
      return;
    }
    create.mutate(
      { name: name.trim(), is_default: makeDefault },
      {
        onSuccess: (created) => {
          onCreated?.(created);
          onClose();
        },
      },
    );
  }

  return (
    <Modal title={editing ? `Rename "${pipeline.name}"` : "New pipeline"} onClose={onClose}>
      <div className="space-y-3">
        <div>
          <label htmlFor="pipeline-name" className={LABEL_CLASS}>
            Pipeline name
          </label>
          <input
            id="pipeline-name"
            value={name}
            maxLength={MAX_NAME_LENGTH}
            onChange={(event) => setName(event.target.value)}
            placeholder="Reactivation"
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            {name.length}/{MAX_NAME_LENGTH} · must be unique in this organization
          </p>
          {showErrors && problem ? <p className="text-xs text-danger">{problem}</p> : null}
        </div>

        {alreadyDefault ? (
          <p className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-text-secondary">
            This is the default pipeline. The default can be moved to another pipeline, but an
            organization always has one — it cannot simply be switched off here.
          </p>
        ) : (
          <label className="flex items-start gap-2 text-sm text-text-secondary">
            <input
              type="checkbox"
              checked={makeDefault}
              onChange={(event) => setMakeDefault(event.target.checked)}
              className="mt-1"
            />
            <span>
              Make this the default pipeline.
              {currentDefault ? (
                <span className="block text-xs text-text-disabled">
                  This moves the default away from “{currentDefault}”.
                </span>
              ) : null}
            </span>
          </label>
        )}

        {!editing ? (
          <p className="text-xs text-text-disabled">
            A new pipeline starts with no stages — add them once it exists.
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
            {pending ? "Saving…" : editing ? "Save changes" : "Create pipeline"}
          </button>
        </div>
      </div>
    </Modal>
  );
}
