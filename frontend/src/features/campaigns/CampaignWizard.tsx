import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect, useMemo, useState } from "react";
import { useForm, useWatch, type FieldPath } from "react-hook-form";
import { useNavigate } from "react-router-dom";

import { ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useCreateCampaign,
  useDispatchCampaign,
  useScheduleCampaign,
  useTemplates,
  useUpdateCampaign,
} from "@/features/campaigns/api";
import { CampaignAudienceStep } from "@/features/campaigns/CampaignAudienceStep";
import { CampaignBasicsStep } from "@/features/campaigns/CampaignBasicsStep";
import { CampaignScheduleFields } from "@/features/campaigns/CampaignScheduleFields";
import type { Delivery } from "@/features/campaigns/CampaignReviewStep";
import { CampaignReviewStep } from "@/features/campaigns/CampaignReviewStep";
import type { CampaignFormValues } from "@/features/campaigns/campaignForm";
import {
  blankCampaign,
  campaignSchema,
  emptyMapping,
  toCreateRequest,
  toUpdateRequest,
} from "@/features/campaigns/campaignForm";
import type { ScheduleDraft } from "@/features/campaigns/scheduleForm";
import { blankSchedule, toScheduleRequest, validateSchedule } from "@/features/campaigns/scheduleForm";
import { templateShape } from "@/features/campaigns/templateShape";
import type { Campaign } from "@/features/campaigns/types";

type StepKey = "basics" | "audience" | "delivery" | "review";

const STEP_LABELS: Record<StepKey, string> = {
  basics: "Message",
  audience: "Audience",
  delivery: "Delivery",
  review: "Review",
};

/** Which fields each step owns, so "Next" validates only what is on screen. */
const STEP_FIELDS: Record<StepKey, FieldPath<CampaignFormValues>[]> = {
  basics: ["name", "phone_number_id", "template_id", "header", "body"],
  audience: ["audience_type", "segment_id", "tag_ids", "contact_ids"],
  delivery: [],
  review: [],
};

const BUTTON_CLASS = "rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50";
const PRIMARY_CLASS = "rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg disabled:opacity-50";

interface Props {
  /** Absent → create a new campaign; present → edit that campaign's definition. */
  campaign?: Campaign;
  /** Prefilled values for a duplicate — a new campaign that starts from an existing one. */
  initialValues?: CampaignFormValues;
}

/**
 * The campaign wizard (Doc 05 B4.2) — one component for create, duplicate and edit.
 *
 * Create walks Message → Audience → Delivery → Review and ends by writing the draft, then applying
 * the chosen delivery through the endpoint that owns it (`/dispatch` or `/schedule`). Edit drops
 * the Delivery step, because scheduling a campaign is a separate decision made on its own page, and
 * ends with a single PATCH carrying `row_version`.
 *
 * Client-side validation mirrors the server's rules so mistakes surface before a round trip; the
 * server re-checks everything and its 422/409 is rendered verbatim.
 */
export function CampaignWizard({ campaign, initialValues }: Props): JSX.Element {
  const navigate = useNavigate();
  const editing = campaign !== undefined;

  const steps: StepKey[] = useMemo(
    () => (editing ? ["basics", "audience", "review"] : ["basics", "audience", "delivery", "review"]),
    [editing],
  );

  const [stepIndex, setStepIndex] = useState(0);
  const [delivery, setDelivery] = useState<Delivery>("draft");
  const [schedule, setSchedule] = useState<ScheduleDraft>(blankSchedule);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  const form = useForm<CampaignFormValues>({
    resolver: zodResolver(campaignSchema),
    defaultValues: initialValues ?? blankCampaign(),
    mode: "onTouched",
  });

  const templates = useTemplates();
  const templateId = useWatch({ control: form.control, name: "template_id" });
  const template = templates.data?.find((candidate) => candidate.id === templateId);

  const create = useCreateCampaign();
  const update = useUpdateCampaign();
  const dispatch = useDispatchCampaign();
  const applySchedule = useScheduleCampaign();

  const { setValue, getValues } = form;

  /**
   * Keep one mapping control per placeholder the chosen template declares. Existing entries are
   * preserved on resize so changing to a template with the same shape does not discard the work,
   * and the server would reject a count mismatch anyway (`count_mismatch`, 422).
   */
  useEffect(() => {
    if (!template) return;
    const shape = templateShape(template);
    for (const [component, wanted] of [
      ["header", shape.headerCount],
      ["body", shape.bodyCount],
    ] as const) {
      const current = getValues(component);
      if (current.length === wanted) continue;
      const next = Array.from({ length: wanted }, (_, index) => current[index] ?? emptyMapping());
      setValue(component, next, { shouldValidate: false });
    }
  }, [template, getValues, setValue]);

  const step = steps[stepIndex] ?? "basics";
  const isLast = stepIndex === steps.length - 1;

  const pending =
    create.isPending || update.isPending || dispatch.isPending || applySchedule.isPending;
  const submitError = create.error ?? update.error ?? dispatch.error ?? applySchedule.error;

  async function next(): Promise<void> {
    if (step === "delivery") {
      const problem = delivery === "schedule" ? validateSchedule(schedule) : null;
      setScheduleError(problem);
      if (problem) return;
    }
    const valid = await form.trigger(STEP_FIELDS[step]);
    if (!valid) return;
    setStepIndex((index) => Math.min(index + 1, steps.length - 1));
  }

  const onSubmit = form.handleSubmit(async (values) => {
    if (editing) {
      update.mutate(
        { campaignId: campaign.id, body: toUpdateRequest(values, campaign.row_version) },
        { onSuccess: (updated) => navigate(`/campaigns/${updated.id}`) },
      );
      return;
    }

    // Create first: dispatch and schedule both act on a campaign that already exists, and both are
    // separate endpoints by design (Doc 04 §17). A failure in either leaves a usable draft behind
    // rather than losing the definition.
    create.mutate(toCreateRequest(values), {
      onSuccess: (created) => {
        const goToDetail = () => navigate(`/campaigns/${created.id}`);
        if (delivery === "now") {
          dispatch.mutate(created.id, { onSuccess: goToDetail, onError: goToDetail });
          return;
        }
        if (delivery === "schedule") {
          applySchedule.mutate(
            { campaignId: created.id, body: toScheduleRequest(schedule) },
            { onSuccess: goToDetail, onError: goToDetail },
          );
          return;
        }
        goToDetail();
      },
    });
  });

  if (templates.isLoading) return <Spinner label="Loading…" />;

  return (
    <form onSubmit={onSubmit}>
      <nav aria-label="Wizard steps" className="mb-4 flex flex-wrap gap-2">
        {steps.map((key, index) => (
          <button
            key={key}
            type="button"
            // Only completed steps are reachable by clicking; going forward runs validation.
            disabled={index > stepIndex}
            onClick={() => setStepIndex(index)}
            aria-current={index === stepIndex ? "step" : undefined}
            className={`rounded-md border px-3 py-1 text-sm ${
              index === stepIndex
                ? "border-accent text-accent"
                : index < stepIndex
                  ? "border-border text-text-secondary hover:bg-hover"
                  : "border-border text-text-disabled"
            }`}
          >
            {index + 1}. {STEP_LABELS[key]}
          </button>
        ))}
      </nav>

      <div className="rounded-lg border border-border bg-surface p-4">
        {step === "basics" ? <CampaignBasicsStep form={form} /> : null}
        {step === "audience" ? <CampaignAudienceStep form={form} /> : null}
        {step === "delivery" ? (
          <div className="space-y-4">
            <fieldset>
              <legend className="text-xs font-medium text-text-secondary">When to send</legend>
              <div className="mt-2 flex flex-wrap gap-2">
                {(
                  [
                    ["draft", "Save as draft"],
                    ["now", "Send immediately"],
                    ["schedule", "Schedule"],
                  ] as const
                ).map(([value, label]) => (
                  <label
                    key={value}
                    className={`cursor-pointer rounded-md border px-3 py-1 text-sm ${
                      delivery === value
                        ? "border-accent text-accent"
                        : "border-border text-text-secondary hover:bg-hover"
                    }`}
                  >
                    <input
                      type="radio"
                      name="delivery"
                      value={value}
                      checked={delivery === value}
                      onChange={() => {
                        setDelivery(value);
                        setScheduleError(null);
                      }}
                      className="sr-only"
                    />
                    {label}
                  </label>
                ))}
              </div>
            </fieldset>

            {delivery === "schedule" ? (
              <CampaignScheduleFields draft={schedule} onChange={setSchedule} />
            ) : null}

            {scheduleError ? <ErrorState message={scheduleError} /> : null}
          </div>
        ) : null}
        {step === "review" ? (
          <CampaignReviewStep
            form={form}
            delivery={editing ? "draft" : delivery}
            schedule={schedule}
            campaignId={campaign?.id}
          />
        ) : null}
      </div>

      {submitError ? (
        <div className="mt-3">
          <ErrorState message={apiErrorMessage(submitError)} />
        </div>
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          className={BUTTON_CLASS}
          onClick={() =>
            stepIndex === 0
              ? navigate(editing ? `/campaigns/${campaign.id}` : "/campaigns")
              : setStepIndex((index) => index - 1)
          }
        >
          {stepIndex === 0 ? "Cancel" : "Back"}
        </button>

        {isLast ? (
          <button type="submit" disabled={pending} className={PRIMARY_CLASS}>
            {pending
              ? "Working…"
              : editing
                ? "Save changes"
                : delivery === "now"
                  ? "Create and send now"
                  : delivery === "schedule"
                    ? "Create and schedule"
                    : "Create draft"}
          </button>
        ) : (
          <button type="button" onClick={() => void next()} className={PRIMARY_CLASS}>
            Next
          </button>
        )}
      </div>
    </form>
  );
}
