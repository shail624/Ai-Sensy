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

/** Honest domain projection: typed CRM attributes render when defined; KYC/SIM data is never invented. */
export function ReactivationSection({ contact, focus = "all" }: { contact: Contact; focus?: "all" | "kyc" | "sim" }): JSX.Element {
  const values = contact.attributes;
  const find = (pattern: RegExp) => Object.entries(values).find(([key]) => pattern.test(key))?.[1];
  return <Section title={focus === "kyc" ? "KYC" : focus === "sim" ? "SIM lifecycle" : "Reactivation readiness"} description="Domain fields appear automatically when supplied as typed CRM attributes; they are not treated as a substitute for future audited workflow records." icon={<Sparkles aria-hidden className="h-4 w-4" />}>{focus === "all" ? <ReadinessRow label="Reactivation status" value={find(/reactivat.*status/i)} icon={BadgeCheck} /> : null}{focus !== "sim" ? <ReadinessRow label="KYC status" value={find(/kyc/i)} icon={FileCheck2} /> : null}{focus !== "kyc" ? <ReadinessRow label="SIM status" value={find(/sim/i)} icon={PackageCheck} /> : null}</Section>;
}
