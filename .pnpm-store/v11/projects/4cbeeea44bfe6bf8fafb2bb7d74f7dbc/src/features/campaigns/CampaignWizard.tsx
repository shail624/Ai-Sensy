import { zodResolver } from "@hookform/resolvers/zod";
import {
  ArrowRight,
  CalendarClock,
  ChevronLeft,
  CircleCheckBig,
  Eye,
  LayoutTemplate,
  Save,
  Send,
  ShieldCheck,
  UsersRound,
} from "lucide-react";
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
import { CampaignWizardProgress } from "@/features/campaigns/CampaignWizardProgress";
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

type StepKey = "audience" | "basics" | "preview" | "delivery" | "approval" | "review";

const STEP_LABELS: Record<StepKey, string> = {
  audience: "Audience",
  basics: "Template",
  preview: "Preview",
  delivery: "Schedule",
  approval: "Approval",
  review: "Confirmation",
};

const STEP_META: Record<
  StepKey,
  { title: string; description: string; icon: typeof UsersRound }
> = {
  audience: {
    title: "Choose your audience",
    description: "Select one saved audience source. Opted-out and invalid contacts stay protected by the server.",
    icon: UsersRound,
  },
  basics: {
    title: "Select the message",
    description: "Name the campaign, choose a WhatsApp number, and use an approved template.",
    icon: LayoutTemplate,
  },
  preview: {
    title: "Preview the experience",
    description: "Check the audience, sender, message, and personalization before choosing delivery.",
    icon: Eye,
  },
  delivery: {
    title: "Choose delivery",
    description: "Keep a draft, send immediately, or schedule delivery for the right time.",
    icon: CalendarClock,
  },
  approval: {
    title: "Confirm readiness",
    description: "Complete the human checkpoint required before a delivery action can continue.",
    icon: ShieldCheck,
  },
  review: {
    title: "Review and confirm",
    description: "One final summary before the existing campaign service creates the draft or starts delivery.",
    icon: CircleCheckBig,
  },
};

/** Which fields each step owns, so "Next" validates only what is on screen. */
const STEP_FIELDS: Record<StepKey, FieldPath<CampaignFormValues>[]> = {
  audience: ["audience_type", "segment_id", "tag_ids", "contact_ids"],
  basics: ["name", "phone_number_id", "template_id", "header", "body"],
  preview: [],
  delivery: [],
  approval: [],
  review: [],
};

const BUTTON_CLASS =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border border-border bg-surface px-4 py-2 text-sm font-semibold text-text-primary transition-colors hover:bg-hover disabled:opacity-50";
const PRIMARY_CLASS =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-accent px-5 py-2 text-sm font-semibold text-accent-fg shadow-sm transition-colors hover:bg-accent-strong disabled:opacity-50";

interface Props {
  /** Absent → create a new campaign; present → edit that campaign's definition. */
  campaign?: Campaign;
  /** Prefilled values for a duplicate — a new campaign that starts from an existing one. */
  initialValues?: CampaignFormValues;
}

/**
 * The campaign wizard (Doc 05 B4.2) — one component for create, duplicate and edit.
 *
 * Create walks Audience → Template → Preview → Schedule → Approval → Send and ends by writing the draft, then applying
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
    () => editing
      ? ["audience", "basics", "preview", "approval", "review"]
      : ["audience", "basics", "preview", "delivery", "approval", "review"],
    [editing],
  );

  const [stepIndex, setStepIndex] = useState(0);
  const [delivery, setDelivery] = useState<Delivery>("draft");
  const [schedule, setSchedule] = useState<ScheduleDraft>(blankSchedule);
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [approvalAcknowledged, setApprovalAcknowledged] = useState(false);

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
  const stepMeta = STEP_META[step];
  const StepIcon = stepMeta.icon;
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
    if (step === "approval" && delivery !== "draft" && !approvalAcknowledged) return;
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
    <form onSubmit={onSubmit} className="mx-auto max-w-5xl">
      <CampaignWizardProgress
        steps={steps.map((key) => ({ key, label: STEP_LABELS[key] }))}
        currentIndex={stepIndex}
        includeAnalytics={!editing}
        onSelect={setStepIndex}
      />

      <section className="mt-4 overflow-hidden rounded-xl border border-border bg-surface shadow-sm">
        <header className="flex items-start gap-3 border-b border-border bg-surface-subtle px-4 py-4 sm:px-5">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent">
            <StepIcon aria-hidden className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-accent">
              Step {stepIndex + 1} of {steps.length}
            </p>
            <h2 className="mt-0.5 text-lg font-bold text-text-primary">{stepMeta.title}</h2>
            <p className="mt-1 text-sm leading-relaxed text-text-secondary">{stepMeta.description}</p>
          </div>
        </header>

        <div className="p-4 sm:p-5">
        {step === "basics" ? <CampaignBasicsStep form={form} /> : null}
        {step === "audience" ? <CampaignAudienceStep form={form} /> : null}
        {step === "preview" ? (
          <CampaignReviewStep form={form} delivery="draft" schedule={schedule} campaignId={campaign?.id} />
        ) : null}
        {step === "delivery" ? (
          <div className="space-y-4">
            <fieldset>
              <legend className="sr-only">When to send</legend>
              <div className="grid gap-3 sm:grid-cols-3">
                {(
                  [
                    ["draft", "Save as draft", "Finish setup later", Save],
                    ["now", "Send now", "Start after confirmation", Send],
                    ["schedule", "Schedule", "Choose date or sequence", CalendarClock],
                  ] as const
                ).map(([value, label, description, Icon]) => (
                  <label
                    key={value}
                    className={`flex cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors ${
                      delivery === value
                        ? "border-accent bg-accent-soft text-accent ring-1 ring-accent"
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
                    <Icon aria-hidden className="mt-0.5 h-5 w-5 shrink-0" />
                    <span>
                      <span className="block text-sm font-semibold text-text-primary">{label}</span>
                      <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
                        {description}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>

            {delivery === "schedule" ? (
              <div className="rounded-xl border border-border bg-surface-subtle p-4">
                <CampaignScheduleFields draft={schedule} onChange={setSchedule} />
              </div>
            ) : null}

            {scheduleError ? <ErrorState message={scheduleError} /> : null}
          </div>
        ) : null}
        {step === "approval" ? (
          <div className="space-y-4">
            <div className="flex items-start gap-3 rounded-xl border border-info bg-info-soft p-4 text-sm text-info-on-soft">
              <ShieldCheck aria-hidden className="mt-0.5 h-5 w-5 shrink-0" />
              <p>
                No server-side approval workflow is configured. Existing campaign permissions remain
                the source of authority; this checkpoint does not change dispatch rules.
              </p>
            </div>
            {delivery === "draft" ? (
              <div className="rounded-xl border border-border bg-surface-subtle p-4 text-sm text-text-secondary">Drafts do not send messages and need no delivery acknowledgement.</div>
            ) : (
              <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-border p-4 hover:bg-hover">
                <input type="checkbox" checked={approvalAcknowledged} onChange={(event) => setApprovalAcknowledged(event.target.checked)} className="mt-0.5 h-4 w-4 accent-accent" />
                <span>
                  <span className="block text-sm font-semibold text-text-primary">I reviewed the audience, template, and delivery timing</span>
                  <span className="mt-1 block text-xs leading-relaxed text-text-secondary">The final action uses the existing permission-gated campaign endpoint. Messages handed to Meta cannot be recalled.</span>
                </span>
              </label>
            )}
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
      </section>

      {submitError ? (
        <div className="mt-3">
          <ErrorState message={apiErrorMessage(submitError)} />
        </div>
      ) : null}

      <div className="sticky bottom-3 z-30 mt-4 flex items-center justify-between gap-3 rounded-xl border border-border bg-surface/95 p-3 shadow-lg backdrop-blur">
        <button
          type="button"
          className={BUTTON_CLASS}
          onClick={() =>
            stepIndex === 0
              ? navigate(editing ? `/campaigns/${campaign.id}` : "/campaigns")
              : setStepIndex((index) => index - 1)
          }
        >
          {stepIndex > 0 ? <ChevronLeft aria-hidden className="h-4 w-4" /> : null}
          {stepIndex === 0 ? "Cancel" : "Back"}
        </button>

        <div className="hidden min-w-0 flex-1 text-center sm:block">
          <p className="truncate text-xs font-semibold text-text-primary">{STEP_LABELS[step]}</p>
          <p className="mt-0.5 text-[11px] text-text-disabled">Nothing sends before confirmation</p>
        </div>

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
            {!pending ? <CircleCheckBig aria-hidden className="h-4 w-4" /> : null}
          </button>
        ) : (
          <button type="button" disabled={step === "approval" && delivery !== "draft" && !approvalAcknowledged} onClick={() => void next()} className={PRIMARY_CLASS}>
            Continue
            <ArrowRight aria-hidden className="h-4 w-4" />
          </button>
        )}
      </div>
    </form>
  );
}
