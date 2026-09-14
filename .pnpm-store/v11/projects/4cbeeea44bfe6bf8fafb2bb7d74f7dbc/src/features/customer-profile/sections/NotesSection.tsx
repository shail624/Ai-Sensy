import { EmptyState, Section } from "@/components/ui";
import type { Note } from "@/features/customer-profile/types";

/**
 * Notes are staff notes on a *conversation* (GET /conversations/{id}/notes); there is no
 * contact-level notes endpoint. This renders the structure and accepts notes when a conversation is
 * in context, otherwise an explanatory empty state.
 */
export function NotesSection({ notes }: { notes?: Note[] }): JSX.Element {
  return (
    <Section title="Notes">
      {!notes || notes.length === 0 ? (
        <EmptyState
          title="No notes"
          description="Staff notes live on conversations and appear here when a conversation is in context."
        />
      ) : (
        <ul className="space-y-2">
          {notes.map((note) => (
            <li key={note.id} className="rounded-md border border-border px-3 py-2 text-sm">
              <p className="text-text-primary">{note.body}</p>
              <p className="mt-1 text-xs text-text-secondary">
                {note.author ?? "Unknown"} · {new Date(note.created_at).toLocaleString()}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
