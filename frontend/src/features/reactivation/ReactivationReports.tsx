import { BarChart3, FileCheck2, PackageCheck, ScanSearch } from "lucide-react";

import { Card, ErrorState, Section, Spinner } from "@/components/ui";
import { AiFoundationPanel } from "@/features/ai";
import { apiErrorMessage, useAnalyticsSummary } from "@/features/analytics/api";
import { EngagementFunnel } from "@/features/analytics/EngagementFunnel";
import { ExportActions } from "@/features/analytics/ExportActions";
import { KpiCards } from "@/features/analytics/KpiCards";
import type { AnalyticsFilterState } from "@/features/analytics/types";

const FILTERS: AnalyticsFilterState = { preset: "last_30d", from: "", to: "", granularity: "day", compare: "" };

/** Executive report shell using only verified analytics rollups. */
export function ReactivationReports(): JSX.Element {
  const summary = useAnalyticsSummary(FILTERS);
  if (summary.isLoading) return <Spinner label="Loading executive reports…" />;
  if (summary.isError) return <ErrorState message={apiErrorMessage(summary.error)} onRetry={() => void summary.refetch()} />;
  return <div className="space-y-5">
    <KpiCards kpis={summary.data?.kpis} />
    <div className="grid gap-4 xl:grid-cols-2"><Section title="Engagement conversion" description="Verified messaging delivery evidence for the last 30 days."><EngagementFunnel totals={summary.data?.totals} /></Section><Section title="Executive export" description="Create governed evidence from the existing reporting contract."><ExportActions filters={FILTERS} /></Section></div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <ReportBoundary icon={BarChart3} title="Reactivation" />
      <ReportBoundary icon={FileCheck2} title="KYC" />
      <ReportBoundary icon={PackageCheck} title="SIM" />
      <ReportBoundary icon={ScanSearch} title="Scan" />
    </div>
    <AiFoundationPanel capabilities={["insights"]} context="verified engagement rollups; reactivation, KYC, SIM, scan, and revenue dimensions remain unavailable" />
  </div>;
}

function ReportBoundary({ icon: Icon, title }: { icon: typeof BarChart3; title: string }): JSX.Element {
  return <Card className="p-4" padding={false}><Icon aria-hidden className="h-5 w-5 text-text-disabled" /><h2 className="mt-3 text-sm font-semibold text-text-primary">{title} report</h2><p className="mt-1 text-xs leading-relaxed text-text-secondary">Awaiting a dedicated domain event and analytics dimension. No zero-value report is fabricated.</p></Card>;
}
