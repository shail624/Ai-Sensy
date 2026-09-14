export interface OperationsSection {
  key: string;
  label: string;
  path: string;
  description: string;
  permission: string;
}

/**
 * Operations destinations stay data-driven so navigation, page context, and permission filtering
 * all read from one source of truth.
 */
export const OPERATIONS_SECTIONS: OperationsSection[] = [
  {
    key: "overview",
    label: "Overview",
    path: "/operations/overview",
    permission: "system:read",
    description: "Operational control center for runtime health, queues, integrations, and evidence.",
  },
  {
    key: "jobs",
    label: "Jobs",
    path: "/operations/jobs",
    description: "Background work the platform has been asked to do, and how it went.",
    permission: "system:read",
  },
  {
    key: "queues",
    label: "Queues & workers",
    path: "/operations/queues",
    description: "Backlog depth, worker coverage and the health of the processing fleet.",
    permission: "system:read",
  },
  {
    key: "health",
    label: "Health",
    path: "/operations/health",
    permission: "system:read",
    description: "Application liveness and dependency readiness from the production probes.",
  },
  {
    key: "logs",
    label: "Logs",
    path: "/operations/logs",
    permission: "system:read",
    description: "Structured logging boundaries and production observability hand-off.",
  },
  {
    key: "api",
    label: "API",
    path: "/operations/api",
    permission: "apikeys:manage",
    description: "Audited API credentials for trusted integrations.",
  },
  {
    key: "webhooks",
    label: "Webhooks",
    path: "/operations/webhooks",
    permission: "waba:read",
    description: "WhatsApp channel connectivity and webhook operating boundaries.",
  },
];

export const OPERATIONS_PERMISSIONS = [...new Set(OPERATIONS_SECTIONS.map((section) => section.permission))];
