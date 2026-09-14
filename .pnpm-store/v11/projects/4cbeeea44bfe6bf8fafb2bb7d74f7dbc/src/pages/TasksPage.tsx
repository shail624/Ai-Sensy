import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { TaskList } from "@/features/tasks";

/** Route page for the Task List module (Doc 14 §10). */
export function TasksPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Tasks" }]} />
      <PageHeader
        eyebrow="Personal productivity"
        title="Tasks"
        description="Your follow-up queue — no lead left without a next action."
      />
      <TaskList />
    </PageContainer>
  );
}
