import { ShieldCheck, Workflow } from "lucide-react";

import { ManagePageHeader } from "@/components/layout";
import { AutomationWorkspace } from "@/features/automation";
import { useAutomations } from "@/features/automation/api";

/** Flows, laid out as the reference Flow Builder: a guide, the active-flows count, then the flows. */
export function AutomationPage(): JSX.Element {
  const all = useAutomations("", "all");
  const flows = (all.data as { data?: { status: string }[] } | undefined)?.data ?? [];
  const active = flows.filter((flow) => flow.status === "published").length;
  const share = flows.length ? Math.round((active / flows.length) * 100) : 0;

  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Flow Builder" />
      <div className="space-y-5 px-4 py-6 sm:px-[30px]">
        <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
          <section className="rounded-[8px] bg-gradient-to-r from-[#eefaf3] to-surface p-5 dark:from-accent-soft">
            <p className="text-[10px] font-semibold uppercase tracking-wide text-[#2f8a4f]">Flows quick guide</p>
            <h2 className="text-base font-semibold text-black dark:text-text-primary">Quick Guide</h2>
            <p className="mt-1 text-sm text-[#6e6e6e] dark:text-text-secondary">
              A flow runs steps for you when something happens — a customer sends a keyword, a tag is added,
              a reminder is due. Build it, test it, then switch it on.
            </p>
            <p className="mt-3 flex items-start gap-2 rounded-md bg-white/70 px-3 py-2 text-xs text-[#4a4a4a] dark:bg-surface-2 dark:text-text-secondary">
              <ShieldCheck aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-[#2f8a4f]" />
              Flows never message customers on their own: any message a flow prepares waits for a team member to approve it.
            </p>
          </section>
          <section className="flex items-center gap-5 rounded-[8px] bg-surface p-5">
            <div
              className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full text-sm font-semibold text-black dark:text-text-primary"
              style={{ background: `conic-gradient(var(--color-nav-bg) ${share * 3.6}deg, #eeeeee 0deg)` }}
              aria-hidden
            >
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-surface">{share}%</span>
            </div>
            <div>
              <h2 className="text-base font-semibold text-black dark:text-text-primary">Active Flows</h2>
              <p className="mt-1 text-2xl font-semibold text-black dark:text-text-primary">
                {active} <span className="text-sm font-normal text-[#6e6e6e]">/ {flows.length} flows active</span>
              </p>
              <p className="mt-1 flex items-center gap-1.5 text-xs text-[#6e6e6e]">
                <Workflow aria-hidden className="h-3.5 w-3.5" /> Drafts and switched-off flows are not counted as active.
              </p>
            </div>
          </section>
        </div>
        <AutomationWorkspace />
      </div>
    </div>
  );
}
