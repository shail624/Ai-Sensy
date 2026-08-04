import {
  BadgeCheck,
  BarChart3,
  FileCheck2,
  FileSpreadsheet,
  FolderLock,
  PackageCheck,
  CheckCheck,
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
  phase: "Connected" | "Foundation";
  operationalGroup: "live" | "foundation";
}

export const REACTIVATION_SECTIONS: ReactivationSection[] = [
  {
    key: "pipeline",
    label: "Customer Pipeline",
    shortLabel: "Pipeline",
    path: "/reactivation/pipeline",
    description: "Prioritize persisted Vi cases by urgency, ownership, reminders, evidence and server-owned lifecycle state.",
    icon: Workflow,
    phase: "Connected",
    operationalGroup: "live",
  },
  {
    key: "kyc",
    label: "KYC Operations",
    shortLabel: "KYC",
    path: "/reactivation/kyc",
    description: "Review tenant-scoped verification cases, protected document references, appointments and separated approvals.",
    icon: FileCheck2,
    phase: "Connected",
    operationalGroup: "live",
  },
  {
    key: "documents",
    label: "Document Center",
    shortLabel: "Documents",
    path: "/reactivation/documents",
    description: "Manage customer-scoped files, immutable versions, verification decisions and expiry.",
    icon: FolderLock,
    phase: "Connected",
    operationalGroup: "live",
  },
  {
    key: "reports",
    label: "Reports",
    shortLabel: "Reports",
    path: "/reactivation/reports",
    description: "Review factual messaging and operational evidence without inventing unavailable domain metrics.",
    icon: BarChart3,
    phase: "Connected",
    operationalGroup: "live",
  },
  {
    key: "eligible",
    label: "Eligible Numbers",
    shortLabel: "Eligible",
    path: "/reactivation/eligible",
    description: "Eligibility remains an evidence step inside persisted cases; a standalone number inventory is not yet authoritative.",
    icon: ScanSearch,
    phase: "Foundation",
    operationalGroup: "foundation",
  },
  {
    key: "bulk",
    label: "Bulk Eligibility",
    shortLabel: "Bulk check",
    path: "/reactivation/bulk-eligibility",
    description: "Large eligibility intake continues through the governed contact import workflow until a reviewed batch contract exists.",
    icon: FileSpreadsheet,
    phase: "Foundation",
    operationalGroup: "foundation",
  },
  {
    key: "interested",
    label: "Interested Customers",
    shortLabel: "Interested",
    path: "/reactivation/interested",
    description: "Qualified customers are managed in the persisted pipeline rather than a duplicate interested-customer list.",
    icon: UsersRound,
    phase: "Foundation",
    operationalGroup: "foundation",
  },
  {
    key: "sim",
    label: "SIM Orders",
    shortLabel: "SIM orders",
    path: "/reactivation/sim-orders",
    description: "SIM Required is a live case status; a separate fulfilment product remains owner-deferred and is not simulated here.",
    icon: PackageCheck,
    phase: "Foundation",
    operationalGroup: "foundation",
  },
  {
    key: "activation",
    label: "Activation Queue",
    shortLabel: "Activation",
    path: "/reactivation/activation",
    description: "Activation Pending is prioritized in Mission Control; a separate activation authority is not introduced.",
    icon: BadgeCheck,
    phase: "Foundation",
    operationalGroup: "foundation",
  },
  {
    key: "completed",
    label: "Completed",
    shortLabel: "Completed",
    path: "/reactivation/completed",
    description: "Completed cases remain queryable in the customer pipeline and source records instead of a duplicate archive.",
    icon: CheckCheck,
    phase: "Foundation",
    operationalGroup: "foundation",
  },
];

export const REACTIVATION_LIVE_SECTIONS = REACTIVATION_SECTIONS.filter(
  (section) => section.operationalGroup === "live",
);

export const REACTIVATION_FOUNDATION_SECTIONS = REACTIVATION_SECTIONS.filter(
  (section) => section.operationalGroup === "foundation",
);
