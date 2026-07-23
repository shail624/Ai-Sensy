import { PageContainer, PageHeader } from "@/components/layout";
import { TaskList } from "@/features/tasks";

/** Route page for the Task List module (Doc 14 §10). */
export function TasksPage(): JSX.Element {
  return (
    <PageContainer>
      <PageHeader
        title="Tasks"
        description="Your follow-up queue — no lead left without a next action."
      />
      <TaskList />
    </PageContainer>
  );
}
