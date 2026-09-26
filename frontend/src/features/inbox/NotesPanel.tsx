import { useState } from "react";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useAddNote, useAssignableUsers, useDeleteNote, useNotes } from "@/features/inbox/api";
import { useHasPermission } from "@/lib/auth";

/** Internal notes — staff-only, never sent to the customer (FR-INB-03). */
export function NotesPanel({ conversationId }: { conversationId: string }): JSX.Element {
  const [draft, setDraft] = useState("");
  const canWrite = useHasPermission("inbox:write");
  const notes = useNotes(conversationId);
  const teammates = useAssignableUsers();
  const addNote = useAddNote(conversationId);
  const deleteNote = useDeleteNote(conversationId);

  return (
    <div className="flex flex-col gap-2">
      <span className="text-xs text-text-secondary">Only your team can see notes. The customer never sees them.</span>

      {notes.isLoading ? (
        <Spinner label="Loading notes…" />
      ) : notes.isError ? (
        <ErrorState message={apiErrorMessage(notes.error)} onRetry={() => void notes.refetch()} />
      ) : (notes.data ?? []).length === 0 ? (
        <EmptyState compact title="No notes yet" />
      ) : (
        <ul className="space-y-2">
          {(notes.data ?? []).map((note) => (
            <li key={note.id} className="rounded-md border border-[#fde68a] bg-[#fffbeb] px-3 py-2 text-sm dark:border-border dark:bg-surface-2">
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
            rows={3}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.ctrlKey || event.metaKey) && draft.trim() && !addNote.isPending) {
                event.preventDefault();
                addNote.mutate(draft.trim(), { onSuccess: () => setDraft("") });
              }
            }}
            placeholder="Write a note… (Ctrl + Enter to save)"
            className="w-full rounded-[8px] bg-[#f0f0f0] px-3 py-2 text-sm text-[#4a4a4a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:bg-surface-2 dark:text-text-primary"
          />
          {(teammates.data ?? []).length > 0 ? (
            <div className="flex gap-1 overflow-x-auto pb-1" aria-label="Mention a teammate">
              {(teammates.data ?? []).slice(0, 8).map((teammate) => (
                <button
                  key={teammate.id}
                  type="button"
                  onClick={() => setDraft((value) => `${value}${value && !value.endsWith(" ") ? " " : ""}@${teammate.full_name} `)}
                  className="shrink-0 rounded-full border border-border px-2 py-1 text-[11px] text-text-secondary hover:bg-hover"
                >
                  @{teammate.full_name}
                </button>
              ))}
            </div>
          ) : null}
          {addNote.error ? <ErrorState message={apiErrorMessage(addNote.error)} /> : null}
          <button
            type="button"
            disabled={!draft.trim() || addNote.isPending}
            onClick={() =>
              addNote.mutate(draft.trim(), { onSuccess: () => setDraft("") })
            }
            className="inline-flex h-9 items-center rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white transition-colors hover:bg-[#08393d] disabled:opacity-60"
          >
            {addNote.isPending ? "Saving…" : "Save note"}
          </button>
        </div>
      ) : null}
    </div>
  );
}
