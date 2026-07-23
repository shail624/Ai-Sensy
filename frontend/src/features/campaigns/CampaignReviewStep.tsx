import { useWatch, type UseFormReturn } from "react-hook-form";

import { DefinitionRow } from "@/components/ui";
import { usePhoneNumbers, useSegments, useTags, useTemplates } from "@/features/campaigns/api";
import type { CampaignFormValues } from "@/features/campaigns/campaignForm";
import { CampaignPreviewPanel } from "@/features/campaigns/CampaignPreviewPanel";
import { formatCount } from "@/features/campaigns/format";
import type { ScheduleDraft } from "@/features/campaigns/scheduleForm";
import { parseSteps } from "@/features/campaigns/scheduleForm";
import { templateShape } from "@/features/campaigns/templateShape";
import { AUDIENCE_TYPE_LABELS, SCHEDULE_TYPE_LABELS } from "@/features/campaigns/types";

export type Delivery = "draft" | "now" | "schedule";

interface Props {
  form: UseFormReturn<CampaignFormValues>;
  delivery: Delivery;
  schedule: ScheduleDraft;
  /** Present when editing — the campaign exists, so its real audience and cost can be shown. */
  campaignId?: string;
}

/**
 * The confirmation step (Doc 05 B4.2) — the whole definition in one place before anything is sent.
 *
 * When creating, audience size and cost are stated as "computed once the draft exists": both are
 * server-side reads of a **materialized roster**, and there is no roster until the draft is
 * created. Saying so is more useful than showing an estimate the server has not made. When editing,
 * the campaign exists and both are shown live.
 */
export function CampaignReviewStep({ form, delivery, schedule, campaignId }: Props): JSX.Element {
  const values = useWatch({ control: form.control }) as Partial<CampaignFormValues>;

  const numbers = usePhoneNumbers();
  const templates = useTemplates();
  const segments = useSegments(values.audience_type === "segment");
  const tags = useTags(values.audience_type === "tag");

  const number = numbers.data?.find((candidate) => candidate.id === values.phone_number_id);
  const template = templates.data?.find((candidate) => candidate.id === values.template_id);
  const segment = segments.data?.find((candidate) => candidate.id === values.segment_id);
  const selectedTags = (tags.data ?? []).filter((tag) => (values.tag_ids ?? []).includes(tag.id));
  const shape = templateShape(template);

  return (
    <div className="space-y-4">
      <dl className="rounded-lg border border-border bg-surface px-4 py-2">
        <DefinitionRow label="Name">{values.name || "—"}</DefinitionRow>
        <DefinitionRow label="Send from">
          {number ? `${number.display_number}${number.verified_name ? ` — ${number.verified_name}` : ""}` : "—"}
        </DefinitionRow>
        <DefinitionRow label="Template">
          {template ? `${template.name} (${template.language})` : "—"}
        </DefinitionRow>
        <DefinitionRow label="Variables">
          {shape.headerCount + shape.bodyCount === 0
            ? "None"
            : `${shape.headerCount} header, ${shape.bodyCount} body`}
        </DefinitionRow>
        <DefinitionRow label="Audience">
          {values.audience_type ? AUDIENCE_TYPE_LABELS[values.audience_type] : "—"}
          {values.audience_type === "segment" && segment ? ` — ${segment.name}` : ""}
          {values.audience_type === "tag" && selectedTags.length > 0
            ? ` — ${selectedTags.map((tag) => tag.name).join(", ")}`
            : ""}
          {values.audience_type === "list"
            ? ` — ${formatCount((values.contact_ids ?? []).length)} contacts`
            : ""}
        </DefinitionRow>
        <DefinitionRow label="Delivery">
          {delivery === "draft"
            ? "Save as draft — nothing is sent"
            : delivery === "now"
              ? "Send immediately after creating"
              : describeSchedule(schedule)}
        </DefinitionRow>
      </dl>

      {template ? (
        <div className="rounded-lg border border-border bg-surface-2 p-3">
          <p className="text-xs font-medium text-text-secondary">Message</p>
          {shape.headerText ? (
            <p className="mt-2 text-sm font-semibold text-text-primary">{shape.headerText}</p>
          ) : null}
          <p className="mt-1 whitespace-pre-wrap text-sm text-text-primary">{shape.bodyText}</p>
          {shape.footerText ? (
            <p className="mt-1 text-xs text-text-disabled">{shape.footerText}</p>
          ) : null}
        </div>
      ) : null}

      {campaignId ? (
        <CampaignPreviewPanel campaignId={campaignId} />
      ) : (
        <p className="rounded-md border border-border bg-surface-2 px-3 py-2 text-xs text-text-secondary">
          The exact audience size, opt-out exclusions and cost estimate are computed from the
          roster once the draft is created — they are shown on the campaign page, before you send.
        </p>
      )}

      {delivery === "now" ? (
        <p className="rounded-md border border-warning px-3 py-2 text-sm text-warning">
          This sends real WhatsApp messages as soon as the campaign is created. Messages already
          handed to Meta cannot be unsent.
        </p>
      ) : null}
    </div>
  );
}

function describeSchedule(schedule: ScheduleDraft): string {
  const label = SCHEDULE_TYPE_LABELS[schedule.schedule_type];
  if (schedule.schedule_type === "one_time") {
    return `${label} — ${schedule.run_at || "no time set"} (${schedule.timezone})`;
  }
  if (schedule.schedule_type === "recurring") {
    return `${label} — ${schedule.cron_expr} (${schedule.timezone})`;
  }
  return `${label} — ${parseSteps(schedule.steps).length} steps from ${
    schedule.starts_at || "no start set"
  } (${schedule.timezone})`;
}
