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
}

export const REACTIVATION_SECTIONS: ReactivationSection[] = [
  { key: "eligible", label: "Eligible Numbers", shortLabel: "Eligible", path: "/reactivation/eligible", description: "Review and segment numbers that can enter the reactivation journey.", icon: ScanSearch, phase: "Foundation" },
  { key: "bulk", label: "Bulk Eligibility", shortLabel: "Bulk check", path: "/reactivation/bulk-eligibility", description: "Prepare large eligibility batches through the existing import workflow.", icon: FileSpreadsheet, phase: "Foundation" },
  { key: "interested", label: "Interested Customers", shortLabel: "Interested", path: "/reactivation/interested", description: "Work qualified customers through the existing CRM workspace.", icon: UsersRound, phase: "Foundation" },
  { key: "pipeline", label: "Customer Pipeline", shortLabel: "Pipeline", path: "/reactivation/pipeline", description: "Manage persisted Vi cases through the approved lifecycle with governed ownership, evidence, tasks, documents and SLA state.", icon: Workflow, phase: "Connected" },
  { key: "kyc", label: "KYC", shortLabel: "KYC", path: "/reactivation/kyc", description: "Coordinate identity-verification work with tasks and governed documents.", icon: FileCheck2, phase: "Foundation" },
  { key: "documents", label: "Document Center", shortLabel: "Documents", path: "/reactivation/documents", description: "Manage customer-scoped files, immutable versions, verification decisions, and expiry.", icon: FolderLock, phase: "Connected" },
  { key: "sim", label: "SIM Orders", shortLabel: "SIM orders", path: "/reactivation/sim-orders", description: "Prepare the future SIM fulfilment workspace without creating order logic.", icon: PackageCheck, phase: "Foundation" },
  { key: "activation", label: "Activation Queue", shortLabel: "Activation", path: "/reactivation/activation", description: "Coordinate the final activation hand-off without inventing activation records.", icon: BadgeCheck, phase: "Foundation" },
  { key: "completed", label: "Completed", shortLabel: "Completed", path: "/reactivation/completed", description: "A governed destination for completed reactivations once domain events are available.", icon: CheckCheck, phase: "Foundation" },
  { key: "reports", label: "Reports", shortLabel: "Reports", path: "/reactivation/reports", description: "Use existing messaging analytics while reactivation KPIs await domain events.", icon: BarChart3, phase: "Connected" },
];
