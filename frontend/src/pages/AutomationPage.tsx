import { ArrowRight, Bot, CheckCircle2, GitBranch, LockKeyhole, Sparkles, Zap } from "lucide-react";
import { Link } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge, Button, Card, CardHeader, EmptyState } from "@/components/ui";

/** Phase 1 navigation foundation only. It intentionally creates no workflow runtime or fake rules. */
export function AutomationPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Automation" }]} />
      <PageHeader
        eyebrow="Governed automation"
        title="Automation"
        description="A clear home for future trigger-and-action workflows, designed around the existing queue, permissions and mandatory approval architecture."
        meta={<><Badge tone="info" dot>Phase 1 foundation</Badge><span>No workflow engine has been started</span></>}
        actions={<Button disabled title="The workflow runtime is a Phase 2 milestone" leftIcon={<Zap className="h-4 w-4" />}>Create automation</Button>}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <AutomationCard icon={GitBranch} title="Trigger with context" description="Inbound messages, stage changes and schedules will enter through the governed event architecture." />
        <AutomationCard icon={CheckCircle2} title="Deterministic actions" description="Safe internal actions will reuse assignments, tags, tasks and notifications instead of duplicating them." />
        <AutomationCard icon={LockKeyhole} title="Human approval" description="Every customer-facing recommendation remains permission-checked, editable and explicitly approved." />
      </div>

      <Card className="mt-6 overflow-hidden" padding={false}>
        <div className="grid lg:grid-cols-[1.2fr_0.8fr]">
          <div className="p-6 sm:p-8">
            <CardHeader title="Built for safe scale" description="The UI is ready; the runtime remains intentionally outside Phase 1." icon={<Bot aria-hidden className="h-5 w-5" />} />
            <div className="mt-6 flex flex-wrap items-center gap-2 text-sm">
              {["Trigger", "Condition", "Internal action", "Approval", "Existing send pipeline"].map((step, index) => (
                <div key={step} className="flex items-center gap-2">
                  <span className="rounded-xl border border-border bg-surface-2 px-3 py-2 font-medium text-text-primary">{step}</span>
                  {index < 4 ? <ArrowRight aria-hidden className="h-4 w-4 text-text-disabled" /> : null}
                </div>
              ))}
            </div>
            <p className="mt-5 max-w-2xl text-sm leading-relaxed text-text-secondary">Phase 2 will attach the versioned workflow runtime to this surface. Until then, no control suggests that an automation can run.</p>
          </div>
          <div className="border-t border-border bg-[linear-gradient(145deg,var(--color-accent-soft),var(--color-bg-surface-2))] p-6 lg:border-l lg:border-t-0">
            <EmptyState compact title="Nothing is running" description="This is an intentional safety state, not missing data." />
            <Link to="/tasks" className="mt-3 block"><Button variant="secondary" block rightIcon={<ArrowRight className="h-4 w-4" />}>Use task workflows today</Button></Link>
          </div>
        </div>
      </Card>
    </PageContainer>
  );
}
function AutomationCard({ icon: Icon, title, description }: { icon: typeof Sparkles; title: string; description: string }): JSX.Element {
  return <Card interactive><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-accent-soft text-accent"><Icon aria-hidden className="h-5 w-5" /></span><h2 className="mt-4 text-base font-semibold text-text-primary">{title}</h2><p className="mt-2 text-sm leading-relaxed text-text-secondary">{description}</p></Card>;
}
