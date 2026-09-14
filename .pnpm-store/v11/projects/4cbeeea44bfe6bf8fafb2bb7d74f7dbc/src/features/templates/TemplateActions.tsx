import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConfirmDialog } from "@/features/campaigns/ConfirmDialog";
import { apiErrorMessage, useDeleteTemplate, useHasPermission } from "@/features/templates/api";
import type { Template } from "@/features/templates/types";
import { isEditable } from "@/features/templates/types";

const ACTION_CLASS =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

interface Props {
  template: Template;
  /** After a delete the detail page must leave; the list just refreshes in place. */
  onDeleted?: () => void;
}

/**
 * The template action set (FR-TPL-02), gated twice over.
 *
 * **By permission**, using the codes the API enforces (Doc 04 §15): `templates:write` to create,
 * edit, clone and delete. **By status**, using the lifecycle predicates in `types.ts` — only a
 * `draft` or `rejected` template is still the platform's to edit; once Meta owns it an edit would
 * be overwritten by the next sync, and the server answers 409. Clone is always offered, because
 * starting a new draft from an approved definition is exactly what an operator does when they
 * cannot edit one.
 *
 * One implementation, used identically by the list rows and the detail page.
 */
export function TemplateActions({ template, onDeleted }: Props): JSX.Element {
  const navigate = useNavigate();
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const canWrite = useHasPermission("templates:write");
  const remove = useDeleteTemplate();

  const editable = isEditable(template);

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex flex-wrap items-center justify-end gap-1">
        {canWrite && editable ? (
          <button
            type="button"
            className={ACTION_CLASS}
            onClick={() => navigate(`/templates/${template.id}/edit`)}
          >
            Edit
          </button>
        ) : null}

        {canWrite ? (
          <button
            type="button"
            className={ACTION_CLASS}
            // Clone is composed from the endpoints that exist: the editor opens prefilled from this
            // template and creates a new one. Nothing is copied server-side.
            onClick={() => navigate("/templates/new", { state: { cloneOf: template } })}
          >
            Clone
          </button>
        ) : null}

        {canWrite ? (
          <button
            type="button"
            className={`${ACTION_CLASS} text-danger`}
            disabled={remove.isPending}
            onClick={() => setConfirmingDelete(true)}
          >
            Delete
          </button>
        ) : null}
      </div>

      {confirmingDelete ? (
        <ConfirmDialog
          title="Delete this template?"
          body={
            template.status === "draft"
              ? `"${template.name}" has never been submitted, so it is removed locally.`
              : `"${template.name}" is withdrawn from Meta and then removed here. Any campaign still referencing it will no longer be able to send.`
          }
          confirmLabel="Delete template"
          destructive
          pending={remove.isPending}
          error={remove.error}
          onClose={() => setConfirmingDelete(false)}
          onConfirm={() =>
            remove.mutate(template.id, {
              onSuccess: () => {
                setConfirmingDelete(false);
                onDeleted?.();
              },
            })
          }
        />
      ) : null}

      {remove.error && !confirmingDelete ? (
        <p className="text-xs text-danger">{apiErrorMessage(remove.error)}</p>
      ) : null}
    </div>
  );
}
