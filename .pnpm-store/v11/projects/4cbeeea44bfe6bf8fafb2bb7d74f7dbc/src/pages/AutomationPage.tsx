import { LockKeyhole } from "lucide-react";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge } from "@/components/ui";
import { AutomationWorkspace } from "@/features/automation";

/** MD5 Phase 2A authoring workspace. Definitions are durable; runtime remains fail-safe absent. */
export function AutomationPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Automation" }]} />
      <PageHeader
        eyebrow="Governed automation"
        title="Automation"
        description="Build, validate and publish recoverable workflow definitions with immutable version history. Execution stays off until the governed runtime is delivered."
        meta={<><Badge tone="info" dot>Versioned authoring</Badge><span>Human approval remains mandatory</span></>}
      />
      <div className="mb-4 flex items-center gap-2 rounded-xl border border-warning/40 bg-warning-soft px-4 py-3 text-sm text-warning"><LockKeyhole aria-hidden className="h-4 w-4 shrink-0" />Customer-facing nodes can only become approval proposals; they never send directly.</div>
      <AutomationWorkspace />
    </PageContainer>
  );
}
