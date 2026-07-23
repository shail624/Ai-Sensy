export interface OperationsSection {
  key: string;
  label: string;
  path: string;
  description: string;
}

/**
 * The two halves of the operations surface, kept as data so the sub-navigation and the page header
 * read one list.
 *
 * Both sit behind `system:read` — a queue is only meaningful alongside the jobs that flow through
 * it, so there is no useful access to one without the other.
 */
export const OPERATIONS_SECTIONS: OperationsSection[] = [
  {
    key: "jobs",
    label: "Jobs",
    path: "/operations/jobs",
    description: "Background work the platform has been asked to do, and how it went.",
  },
  {
    key: "queues",
    label: "Queues & workers",
    path: "/operations/queues",
    description: "Backlog depth, worker coverage and the health of the processing fleet.",
  },
];
