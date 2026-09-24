import { useWatch, type UseFormReturn } from "react-hook-form";

import { usePhoneNumbers } from "@/features/campaigns/api";
import type { CampaignFormValues } from "@/features/campaigns/campaignForm";

/** The reference's three stages, and which of the wizard's steps each one covers. */
export const CAMPAIGN_STAGES: { label: string; steps: string[] }[] = [
  { label: "Campaign Details", steps: ["audience"] },
  { label: "Create Message", steps: ["basics", "preview"] },
  { label: "Test & Preview", steps: ["delivery", "approval", "review"] },
];

export function stageIndexFor(step: string): number {
  const index = CAMPAIGN_STAGES.findIndex((stage) => stage.steps.includes(step));
  return index < 0 ? 0 : index;
}

/** The reference "Create Campaign" tab strip: where you are in the three big stages. */
export function CampaignStageBar({ step }: { step: string }): JSX.Element {
  const current = stageIndexFor(step);
  return (
    <div role="list" aria-label="Campaign stages" className="flex overflow-x-auto rounded-[8px] bg-surface">
      {CAMPAIGN_STAGES.map((stage, index) => {
        const active = index === current;
        const done = index < current;
        return (
          <div
            key={stage.label}
            role="listitem"
            aria-current={active ? "step" : undefined}
            className={`flex min-w-[150px] flex-1 items-center justify-center gap-2 border-b-[3px] px-4 py-3 text-sm font-medium ${
              active
                ? "border-[var(--color-nav-bg)] text-[var(--color-nav-bg)] dark:text-accent"
                : done
                  ? "border-transparent text-[#2f8a4f]"
                  : "border-transparent text-[#9e9e9e]"
            }`}
          >
            <span
              className={`flex h-6 w-6 items-center justify-center rounded-full text-xs ${
                active ? "bg-[var(--color-nav-bg)] text-white" : done ? "bg-[#dcfce7] text-[#15803d]" : "bg-[#f0f0f0] text-[#9e9e9e]"
              }`}
            >
              {done ? "✓" : index + 1}
            </span>
            {stage.label}
          </div>
        );
      })}
    </div>
  );
}

const QUALITY: Record<string, { label: string; tone: string }> = {
  GREEN: { label: "High", tone: "text-[#15803d]" },
  YELLOW: { label: "Medium", tone: "text-[#b45309]" },
  RED: { label: "Low", tone: "text-[#b91c1c]" },
};

function tierLabel(tier: string | null | undefined): string {
  if (!tier) return "—";
  const match = /TIER_(\d+)(K?)/i.exec(tier);
  if (!match) return tier.replace(/_/g, " ");
  return `${match[1]}${match[2] ? "K" : ""} customers / 24 hours`;
}

/** The reference's strip above the wizard: the sending number's quality and messaging limit. */
export function NumberHealthStrip({ form }: { form: UseFormReturn<CampaignFormValues> }): JSX.Element | null {
  const numbers = usePhoneNumbers();
  const chosen = useWatch({ control: form.control, name: "phone_number_id" });
  const list = numbers.data ?? [];
  const number = list.find((candidate) => candidate.id === chosen) ?? list.find((candidate) => candidate.is_default) ?? list[0];
  if (!number) return null;
  const quality = QUALITY[(number.quality_rating ?? "").toUpperCase()];
  return (
    <div className="grid grid-cols-1 gap-3 rounded-[8px] bg-surface p-4 text-sm sm:grid-cols-3">
      <div>
        <p className="text-xs text-[#808080]">Sending number</p>
        <p className="font-medium text-black dark:text-text-primary">{number.display_number}</p>
      </div>
      <div>
        <p className="text-xs text-[#808080]">Quality Rating</p>
        <p className={`font-semibold ${quality?.tone ?? "text-[#6e6e6e]"}`}>{quality?.label ?? "Not rated yet"}</p>
      </div>
      <div>
        <p className="text-xs text-[#808080]">Template Messaging Tier</p>
        <p className="font-medium text-black dark:text-text-primary">{tierLabel(number.messaging_tier)}</p>
      </div>
    </div>
  );
}
