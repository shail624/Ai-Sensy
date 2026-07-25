import { LockKeyhole, Zap } from "lucide-react";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge, Button } from "@/components/ui";
import { AutomationBuilder } from "@/features/automation";

/** Phase 3 visual blueprint surface. Runtime and persistence remain contract-gated and fail-safe. */
export function AutomationPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Automation" }]} />
      <PageHeader
        eyebrow="Governed automation"
        title="Automation"
        description="Design governed trigger, condition, delay, internal-action, campaign, webhook and approval flows without creating an autonomous send path."
        meta={<><Badge tone="info" dot>Phase 3 blueprint</Badge><span>Human approval remains mandatory</span></>}
        actions={<Button disabled title="Automation persistence is not in the current API contract" leftIcon={<Zap className="h-4 w-4" />}>Publish automation</Button>}
      />
      <div className="mb-4 flex items-center gap-2 rounded-xl border border-warning/40 bg-warning-soft px-4 py-3 text-sm text-warning"><LockKeyhole aria-hidden className="h-4 w-4 shrink-0" />Customer-facing nodes can only become approval proposals; they never send directly.</div>
      <AutomationBuilder />
    </PageContainer>
  );
}
