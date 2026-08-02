import { BadgeCheck, FileCheck2, PackageCheck, Sparkles } from "lucide-react";

import { Badge, EmptyState, ErrorState, Section, Skeleton } from "@/components/ui";
import type { Contact } from "@/features/customer-profile/types";
import { apiErrorMessage, useContactKycCases } from "@/features/kyc/api";
import { KYC_STATUS_LABELS } from "@/features/kyc/types";
import { useHasPermission } from "@/lib/auth";

interface ReadinessRowProps {
  label: string;
  value: unknown;
  icon: typeof Sparkles;
}
function ReadinessRow({ label, value, icon: Icon }: ReadinessRowProps): JSX.Element {
  const available = value !== null && value !== undefined && value !== "";
  return <div className="flex items-center gap-3 border-b border-border py-3 last:border-0"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface-2 text-text-secondary"><Icon aria-hidden className="h-4 w-4" /></span><div className="min-w-0 flex-1"><p className="text-sm font-medium text-text-primary">{label}</p><p className="mt-0.5 truncate text-xs text-text-secondary">{available ? String(value) : "Awaiting the dedicated domain API"}</p></div><Badge tone={available ? "success" : "neutral"}>{available ? "Available" : "Not connected"}</Badge></div>;
}

/** Honest domain projection: typed CRM attributes render when defined; KYC/SIM data is never invented. */
export function ReactivationSection({ contact, focus = "all" }: { contact: Contact; focus?: "all" | "kyc" | "sim" }): JSX.Element {
  const canReadKyc = useHasPermission("kyc:read");
  const kyc = useContactKycCases(contact.id, focus === "kyc" && canReadKyc);
  if (focus === "kyc") {
    if (!canReadKyc) return <EmptyState title="KYC projection is restricted" description="Your role cannot view this customer's KYC case." />;
    if (kyc.isLoading) return <Section title="KYC"><Skeleton className="h-28 w-full" /></Section>;
    if (kyc.isError) return <ErrorState message={apiErrorMessage(kyc.error)} onRetry={() => void kyc.refetch()} />;
    const record = kyc.data?.[0];
    if (!record) return <EmptyState title="No KYC case" description="KYC begins from an eligible Reactivation case; no inferred customer state is shown." />;
    const checks = [
      ["Original holder", record.holder_verified],
      ["Delhi presence", record.delhi_presence_verified],
      ["Active Delhi number", record.active_delhi_number_verified],
    ] as const;
    return <Section title="Governed KYC projection" description="This Customer 360 view reads the same tenant-scoped KYC authority used by Operations." icon={<FileCheck2 aria-hidden className="h-4 w-4" />}><div className="flex items-center justify-between rounded-xl border border-border bg-surface-2 p-3"><div><p className="text-sm font-semibold text-text-primary">KYC status</p><p className="mt-0.5 text-xs text-text-secondary">Updated {new Date(record.updated_at).toLocaleString()} · version {record.row_version}</p></div><Badge tone={record.status === "approved" ? "success" : record.status === "rejected" ? "danger" : "warning"}>{KYC_STATUS_LABELS[record.status]}</Badge></div><div className="mt-3 grid gap-2 sm:grid-cols-3">{checks.map(([label, complete]) => <div key={label} className="rounded-xl border border-border p-3"><p className="text-xs font-medium text-text-secondary">{label}</p><p className={`mt-1 text-sm font-semibold ${complete ? "text-success" : "text-warning"}`}>{complete ? "Verified" : "Required"}</p></div>)}</div></Section>;
  }
  const values = contact.attributes;
  const find = (pattern: RegExp) => Object.entries(values).find(([key]) => pattern.test(key))?.[1];
  return <Section title={focus === "sim" ? "SIM lifecycle" : "Reactivation readiness"} description="Domain fields appear automatically when supplied as typed CRM attributes; they are not treated as a substitute for future audited workflow records." icon={<Sparkles aria-hidden className="h-4 w-4" />}>{focus === "all" ? <><ReadinessRow label="Reactivation status" value={find(/reactivat.*status/i)} icon={BadgeCheck} /><ReadinessRow label="KYC status" value={find(/kyc/i)} icon={FileCheck2} /></> : null}<ReadinessRow label="SIM status" value={find(/sim/i)} icon={PackageCheck} /></Section>;
}
