import { EmptyState, Section } from "@/components/ui";

/**
 * Assignment lives on a *conversation* (`assigned_to`), not a contact — the schema has no contact
 * assignee. Displays the assigned agent when one is supplied in context.
 */
export function AssignmentSection({ assignedAgent }: { assignedAgent?: string | null }): JSX.Element {
  return (
    <Section title="Assignment">
      {assignedAgent ? (
        <p className="text-sm text-text-primary">
          Assigned to <span className="font-medium">{assignedAgent}</span>
        </p>
      ) : (
        <EmptyState
          title="No assignment"
          description="Assignment applies to conversations — open a conversation to see or change its assigned agent."
        />
      )}
    </Section>
  );
}
