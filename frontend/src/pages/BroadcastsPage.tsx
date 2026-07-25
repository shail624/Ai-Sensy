import { BarChart3, Layers3, ShieldCheck } from "lucide-react";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Card } from "@/components/ui";
import { CampaignList } from "@/features/campaigns";

/** Dedicated marketer-facing view over the existing campaign engine. */
export function BroadcastsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Broadcast Center" }]} />
      <PageHeader
        eyebrow="Customer engagement"
        title="Broadcast Center"
        description="Plan, launch, and monitor high-volume WhatsApp engagement from one governed workspace."
      />

      <div className="mb-6 grid gap-3 md:grid-cols-3">
        {[
          { icon: Layers3, title: "One campaign engine", text: "Broadcasts reuse the existing audience, scheduling, pacing, and retry authority." },
          { icon: ShieldCheck, title: "Compliance by default", text: "Opt-out exclusion, approved templates, permissions, and rate gates remain enforced." },
          { icon: BarChart3, title: "Results stay connected", text: "Every broadcast opens into the existing recipient, delivery, cost, and analytics evidence." },
        ].map(({ icon: Icon, title, text }) => (
          <Card key={title} className="p-4" padding={false}>
            <Icon aria-hidden className="h-5 w-5 text-accent" />
            <h2 className="mt-3 text-sm font-semibold text-text-primary">{title}</h2>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">{text}</p>
          </Card>
        ))}
      </div>

      <CampaignList />
    </PageContainer>
  );
}
