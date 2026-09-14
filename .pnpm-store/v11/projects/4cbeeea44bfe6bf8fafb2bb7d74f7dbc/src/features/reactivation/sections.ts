import {
  BadgeCheck,
  BarChart3,
  CheckCheck,
  FileCheck2,
  FileSpreadsheet,
  FolderLock,
  PackageCheck,
  ScanSearch,
  UsersRound,
  Workflow,
  type LucideIcon,
} from "lucide-react";

export interface ReactivationSection {
  key: string;
  label: string;
  shortLabel: string;
  path: string;
  description: string;
  icon: LucideIcon;
  permission: string;
  phase: "Connected" | "Foundation";
}

export const REACTIVATION_SECTIONS: ReactivationSection[] = [
  {
    key: "eligible",
    label: "Eligible Numbers",
    shortLabel: "Eligible",
    path: "/reactivation/eligible",
    description: "Resolve to the existing Reactivation CRM without creating a separate eligibility authority.",
    icon: ScanSearch,
    permission: "reactivation:read",
    phase: "Foundation",
  },
  {
    key: "bulk",
    label: "Bulk Eligibility",
    shortLabel: "Bulk check",
    path: "/reactivation/bulk-eligibility",
    description: "Resolve to the governed Contact import workflow instead of a duplicate batch engine.",
    icon: FileSpreadsheet,
    permission: "contacts:write",
    phase: "Foundation",
  },
  {
    key: "interested",
    label: "Interested Customers",
    shortLabel: "Interested",
    path: "/reactivation/interested",
    description: "Resolve to Lead Confirmed cases in the existing Reactivation CRM.",
    icon: UsersRound,
    permission: "reactivation:read",
    phase: "Foundation",
  },
  {
    key: "pipeline",
    label: "Reactivation CRM",
    shortLabel: "Pipeline",
    path: "/reactivation/pipeline",
    description:
      "Prioritize persisted cases by status, ownership, reminders, SLA risk, documents, and next action.",
    icon: Workflow,
    permission: "reactivation:read",
    phase: "Connected",
  },
  {
    key: "kyc",
    label: "KYC Operations",
    shortLabel: "KYC",
    path: "/reactivation/kyc",
    description:
      "Review tenant-scoped verification cases, protected document references, appointments, and separated approvals.",
    icon: FileCheck2,
    permission: "kyc:read",
    phase: "Connected",
  },
  {
    key: "documents",
    label: "Document Center",
    shortLabel: "Documents",
    path: "/reactivation/documents",
    description:
      "Manage customer-scoped files, immutable versions, verification decisions, and expiry.",
    icon: FolderLock,
    permission: "documents:read",
    phase: "Connected",
  },
  {
    key: "sim",
    label: "SIM Orders",
    shortLabel: "SIM orders",
    path: "/reactivation/sim-orders",
    description: "Resolve to SIM Required cases without introducing a heavy fulfilment workspace.",
    icon: PackageCheck,
    permission: "reactivation:read",
    phase: "Foundation",
  },
  {
    key: "activation",
    label: "Activation Queue",
    shortLabel: "Activation",
    path: "/reactivation/activation",
    description: "Resolve to Activation Pending cases without duplicating activation records.",
    icon: BadgeCheck,
    permission: "reactivation:read",
    phase: "Foundation",
  },
  {
    key: "completed",
    label: "Completed",
    shortLabel: "Completed",
    path: "/reactivation/completed",
    description: "Resolve to completed cases in the existing Reactivation CRM.",
    icon: CheckCheck,
    permission: "reactivation:read",
    phase: "Foundation",
  },
  {
    key: "reports",
    label: "Reports",
    shortLabel: "Reports",
    path: "/reactivation/reports",
    description:
      "Review factual analytics already exposed by the existing reporting authority.",
    icon: BarChart3,
    permission: "analytics:read",
    phase: "Connected",
  },
];
