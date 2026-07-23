import { useState } from "react";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useAddNote, useDeleteNote, useNotes } from "@/features/inbox/api";
import { useHasPermission } from "@/lib/auth";

/** Internal notes — staff-only, never sent to the customer (FR-INB-03). */
export function NotesPanel({ conversationId }: { conversationId: string }): JSX.Element {
  const [draft, setDraft] = useState("");
  const canWrite = useHasPermission("inbox:write");
  const notes = useNotes(conversationId);
  const addNote = useAddNote(conversationId);
  const deleteNote = useDeleteNote(conversationId);

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs font-medium text-text-secondary">Internal notes</span>

      {notes.isLoading ? (
        <Spinner label="Loading notes…" />
      ) : notes.isError ? (
        <ErrorState message={apiErrorMessage(notes.error)} onRetry={() => void notes.refetch()} />
      ) : (notes.data ?? []).length === 0 ? (
        <EmptyState title="No notes" description="Notes are visible to your team only." />
      ) : (
        <ul className="space-y-2">
          {(notes.data ?? []).map((note) => (
            <li key={note.id} className="rounded-md border border-border px-2 py-1.5 text-sm">
              <p className="whitespace-pre-wrap text-text-primary">{note.body}</p>
              <div className="mt-1 flex items-center justify-between gap-2 text-xs text-text-secondary">
                <span>
                  {note.author ?? "Unknown"} · {new Date(note.created_at).toLocaleString()}
                </span>
                {canWrite ? (
                  <button
                    type="button"
                    aria-label={`Delete note ${note.id}`}
                    disabled={deleteNote.isPending}
                    onClick={() => deleteNote.mutate(note.id)}
                    className="rounded px-1 text-text-secondary hover:bg-hover disabled:opacity-50"
                  >
                    ×
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {canWrite ? (
        <div className="space-y-1">
          <label htmlFor="note-body" className="sr-only">
            Add an internal note
          </label>
          <textarea
            id="note-body"
            rows={2}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder="Add an internal note…"
            className="w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary"
          />
          {addNote.error ? <ErrorState message={apiErrorMessage(addNote.error)} /> : null}
          <button
            type="button"
            disabled={!draft.trim() || addNote.isPending}
            onClick={() =>
              addNote.mutate(draft.trim(), { onSuccess: () => setDraft("") })
            }
            className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover disabled:opacity-50"
          >
            {addNote.isPending ? "Saving…" : "Add note"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
