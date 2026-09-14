import { BarChart3, Bot, Lightbulb, MessageSquareText, Sparkles, Users } from "lucide-react";
import { useState } from "react";

import { Badge, Card } from "@/components/ui";

export type AiCapability =
  | "reply"
  | "summary"
  | "document"
  | "campaign"
  | "template"
  | "audience"
  | "insights";

const CAPABILITIES: Record<AiCapability, { label: string; description: string; icon: typeof Bot }> = {
  reply: { label: "AI reply", description: "Draft a grounded reply for an agent to review and send.", icon: MessageSquareText },
  summary: { label: "AI summary", description: "Condense the conversation into an editable customer brief.", icon: Sparkles },
  document: { label: "Document summary", description: "Prepare a source-linked document brief for a human verifier.", icon: Sparkles },
  campaign: { label: "Campaign suggestions", description: "Suggest an objective, tone, and compliant campaign outline.", icon: Lightbulb },
  template: { label: "Template suggestions", description: "Draft template structure for review before Meta submission.", icon: MessageSquareText },
  audience: { label: "Audience suggestions", description: "Recommend reusable audiences without changing segment rules.", icon: Users },
  insights: { label: "Analytics insights", description: "Explain verified metrics without inventing data or outcomes.", icon: BarChart3 },
};

interface Props {
  capabilities: AiCapability[];
  context: string;
  compact?: boolean;
}

/**
 * Phase 2 integration seam for the deferred AI module.
 *
 * It intentionally performs no generation: there is no AI provider/policy API in the current
 * contract. Selecting a capability explains the future human-approved workflow while keeping all
 * customer actions disabled and honest.
 */
export function AiFoundationPanel({ capabilities, context, compact = false }: Props): JSX.Element {
  const [selected, setSelected] = useState<AiCapability>(capabilities[0] ?? "summary");
  const active = CAPABILITIES[selected];
  const ActiveIcon = active.icon;

  return (
    <Card className={compact ? "p-3" : "overflow-hidden"} padding={false}>
      <div className={`flex flex-wrap items-center justify-between gap-3 border-b border-border ${compact ? "p-3" : "p-5"}`}>
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
            <Bot aria-hidden className="h-5 w-5" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-text-primary">AI copilot</h2>
            <p className="text-xs text-text-secondary">Human-approved assistance foundation</p>
          </div>
        </div>
        <Badge tone="neutral">Provider not connected</Badge>
      </div>

      <div className={compact ? "p-3" : "grid gap-0 md:grid-cols-[14rem_1fr]"}>
        <div className={`flex gap-2 overflow-x-auto ${compact ? "pb-3" : "border-b border-border p-3 md:flex-col md:border-b-0 md:border-r"}`}>
          {capabilities.map((capability) => {
            const item = CAPABILITIES[capability];
            const Icon = item.icon;
            return (
              <button
                key={capability}
                type="button"
                aria-pressed={selected === capability}
                onClick={() => setSelected(capability)}
                className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-xl px-3 py-2 text-left text-xs font-medium transition-colors ${selected === capability ? "bg-accent-soft text-accent" : "text-text-secondary hover:bg-hover hover:text-text-primary"}`}
              >
                <Icon aria-hidden className="h-4 w-4" />
                {item.label}
              </button>
            );
          })}
        </div>

        <div className={compact ? "rounded-xl bg-surface-2 p-4" : "p-5"}>
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-surface-2 text-accent">
            <ActiveIcon aria-hidden className="h-5 w-5" />
          </span>
          <h3 className="mt-3 text-sm font-semibold text-text-primary">{active.label}</h3>
          <p className="mt-1 text-sm leading-relaxed text-text-secondary">{active.description}</p>
          <p className="mt-3 rounded-xl border border-border bg-surface-subtle px-3 py-2 text-xs leading-relaxed text-text-secondary">
            Context ready: {context}. Generation stays unavailable until the governed AI service,
            interaction record, confidence scoring, and approval API are delivered.
          </p>
          <div className="mt-3 flex items-center gap-2 text-xs font-medium text-success">
            <span aria-hidden className="h-2 w-2 rounded-full bg-success" />
            Nothing is generated or sent automatically
          </div>
        </div>
      </div>
    </Card>
  );
}
