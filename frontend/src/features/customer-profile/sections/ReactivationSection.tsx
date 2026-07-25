import { BadgeCheck, FileCheck2, PackageCheck, Sparkles } from "lucide-react";

import { Badge, Section } from "@/components/ui";
import type { Contact } from "@/features/customer-profile/types";

interface ReadinessRowProps {
  label: string;
  value: unknown;
  icon: typeof Sparkles;
}
function ReadinessRow({ label, value, icon: Icon }: ReadinessRowProps): JSX.Element {
  const available = value !== null && value !== undefined && value !== "";
  return <div className="flex items-center gap-3 border-b border-border py-3 last:border-0"><span className="flex h-9 w-9 items-center justify-center rounded-xl bg-surface-2 text-text-secondary"><Icon aria-hidden className="h-4 w-4" /></span><div className="min-w-0 flex-1"><p className="text-sm font-medium text-text-primary">{label}</p><p className="mt-0.5 truncate text-xs text-text-secondary">{available ? String(value) : "Awaiting the dedicated domain API"}</p></div><Badge tone={available ? "success" : "neutral"}>{available ? "Available" : "Not connected"}</Badge></div>;
}

/** Honest Phase 1 projection: custom fields render when defined; KYC/SIM data is never invented. */
export function ReactivationSection({ contact }: { contact: Contact }): JSX.Element {
  const values = contact.attributes;
  const find = (pattern: RegExp) => Object.entries(values).find(([key]) => pattern.test(key))?.[1];
  return <Section title="Reactivation readiness" description="Domain fields appear automatically when supplied as typed CRM attributes." icon={<Sparkles aria-hidden className="h-4 w-4" />}><ReadinessRow label="Reactivation status" value={find(/reactivat.*status/i)} icon={BadgeCheck} /><ReadinessRow label="KYC status" value={find(/kyc/i)} icon={FileCheck2} /><ReadinessRow label="SIM status" value={find(/sim/i)} icon={PackageCheck} /></Section>;
}
