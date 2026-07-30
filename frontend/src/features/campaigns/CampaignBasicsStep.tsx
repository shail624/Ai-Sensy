import { MessageCircle } from "lucide-react";
import { useWatch, type UseFormReturn } from "react-hook-form";

import { EmptyState, ErrorState, Spinner } from "@/components/ui";
import { apiErrorMessage, useAttributeDefinitions, usePhoneNumbers, useTemplates } from "@/features/campaigns/api";
import type { CampaignFormValues } from "@/features/campaigns/campaignForm";
import { MAPPABLE_FIELDS, templateShape } from "@/features/campaigns/templateShape";

const FIELD_CLASS =
  "min-h-11 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft";
const LABEL_CLASS = "mb-1.5 block text-sm font-semibold text-text-primary";

interface Props {
  form: UseFormReturn<CampaignFormValues>;
}

/**
 * Step 1 — what is sent, and from where (Doc 05 B4.2).
 *
 * The template picker offers only sendable templates: Meta must have approved a template before it
 * can be broadcast, and the server refuses the rest with `TemplateNotEligible`. Once a template is
 * chosen, one mapping control is drawn per placeholder it declares.
 */
export function CampaignBasicsStep({ form }: Props): JSX.Element {
  const { register, control, formState } = form;
  const errors = formState.errors;

  const numbers = usePhoneNumbers();
  const templates = useTemplates();
  const attributes = useAttributeDefinitions();

  const templateId = useWatch({ control, name: "template_id" });
  const header = useWatch({ control, name: "header" }) ?? [];
  const body = useWatch({ control, name: "body" }) ?? [];

  const template = templates.data?.find((candidate) => candidate.id === templateId);
  const shape = templateShape(template);
  const sendable = (templates.data ?? []).filter((candidate) => candidate.is_sendable);

  if (numbers.isLoading || templates.isLoading) return <Spinner label="Loading templates…" />;

  if (numbers.isError || templates.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(numbers.error ?? templates.error)}
        onRetry={() => {
          void numbers.refetch();
          void templates.refetch();
        }}
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="rounded-xl border border-border bg-surface-subtle p-4">
        <div>
          <label htmlFor="campaign-name" className={LABEL_CLASS}>
            Campaign name
          </label>
          <input
            id="campaign-name"
            {...register("name")}
            placeholder="e.g. July reactivation offer"
            className={FIELD_CLASS}
          />
          {errors.name ? <p className="mt-1 text-xs text-danger">{errors.name.message}</p> : null}
        </div>

        <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
          <label htmlFor="campaign-number" className={LABEL_CLASS}>
            Send from
          </label>
          <select id="campaign-number" {...register("phone_number_id")} className={FIELD_CLASS}>
            <option value="">Choose a number…</option>
            {(numbers.data ?? []).map((number) => (
              <option key={number.id} value={number.id}>
                {number.display_number}
                {number.verified_name ? ` — ${number.verified_name}` : ""}
                {number.quality_rating ? ` (${number.quality_rating})` : ""}
              </option>
            ))}
          </select>
          {errors.phone_number_id ? (
            <p className="mt-1 text-xs text-danger">{errors.phone_number_id.message}</p>
          ) : null}
          {(numbers.data ?? []).length === 0 ? (
            <p className="mt-1 text-xs text-text-disabled">
              No WhatsApp numbers are connected yet.
            </p>
          ) : null}
          </div>

          <div>
          <label htmlFor="campaign-template" className={LABEL_CLASS}>
            Approved template
          </label>
          <select id="campaign-template" {...register("template_id")} className={FIELD_CLASS}>
            <option value="">Choose a template…</option>
            {sendable.map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.name} ({candidate.language}) — {candidate.category}
              </option>
            ))}
          </select>
          {errors.template_id ? (
            <p className="mt-1 text-xs text-danger">{errors.template_id.message}</p>
          ) : null}
          {sendable.length === 0 ? (
            <p className="mt-1 text-xs text-text-disabled">
              No approved templates are available to broadcast.
            </p>
          ) : null}
          </div>
        </div>
      </div>

      {template ? (
        <div className="rounded-xl border border-border bg-surface-subtle p-4">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-text-primary">
            <MessageCircle aria-hidden className="h-4 w-4 text-accent" />
            Customer preview
          </div>
          <div className="max-w-xl rounded-xl border border-border bg-surface p-4 shadow-sm">
            {shape.mediaHeaderFormat ? (
              <p className="text-xs font-semibold uppercase tracking-wide text-text-disabled">
                {shape.mediaHeaderFormat} header
              </p>
            ) : shape.headerText ? (
              <p className="text-sm font-semibold text-text-primary">{shape.headerText}</p>
            ) : null}
            <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
              {shape.bodyText}
            </p>
            {shape.footerText ? (
              <p className="mt-2 text-xs text-text-disabled">{shape.footerText}</p>
            ) : null}
          </div>
        </div>
      ) : null}

      {template && shape.headerCount + shape.bodyCount > 0 ? (
        <div className="space-y-3 rounded-xl border border-border p-4">
          <div>
            <h3 className="text-sm font-semibold text-text-primary">Variable mapping</h3>
            <p className="mt-1 text-xs text-text-secondary">
              Each placeholder gets its value per contact. A fallback matters: WhatsApp rejects an
              empty parameter, so a contact missing the mapped value would fail without one.
            </p>
          </div>

          {shape.headerCount > 0
            ? header.slice(0, shape.headerCount).map((_, index) => (
                <MappingRow
                  key={`header-${index}`}
                  form={form}
                  component="header"
                  index={index}
                  attributeKeys={(attributes.data ?? []).map((definition) => ({
                    value: definition.key_name,
                    label: definition.label,
                  }))}
                />
              ))
            : null}

          {body.slice(0, shape.bodyCount).map((_, index) => (
            <MappingRow
              key={`body-${index}`}
              form={form}
              component="body"
              index={index}
              attributeKeys={(attributes.data ?? []).map((definition) => ({
                value: definition.key_name,
                label: definition.label,
              }))}
            />
          ))}
        </div>
      ) : template ? (
        <EmptyState
          title="This template has no variables"
          description="Nothing to map — every recipient receives the same text."
        />
      ) : null}
    </div>
  );
}

interface MappingRowProps {
  form: UseFormReturn<CampaignFormValues>;
  component: "header" | "body";
  index: number;
  attributeKeys: { value: string; label: string }[];
}

/** One `{{n}}` placeholder: where its value comes from, and what to use when there isn't one. */
function MappingRow({ form, component, index, attributeKeys }: MappingRowProps): JSX.Element {
  const { register, control } = form;
  const source = useWatch({ control, name: `${component}.${index}.source` });
  const fieldError = form.formState.errors[component]?.[index];

  return (
    <div className="rounded-xl border border-border bg-surface-subtle p-3">
      <p className="mb-2 text-xs font-medium text-text-secondary">
        {component === "header" ? "Header" : "Body"} variable {`{{${index + 1}}}`}
      </p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <div>
          <label htmlFor={`${component}-${index}-source`} className={LABEL_CLASS}>
            Source
          </label>
          <select
            id={`${component}-${index}-source`}
            {...register(`${component}.${index}.source`)}
            className={FIELD_CLASS}
          >
            <option value="field">Contact field</option>
            <option value="attribute">Custom attribute</option>
            <option value="literal">Fixed text</option>
          </select>
        </div>

        <div>
          <label htmlFor={`${component}-${index}-key`} className={LABEL_CLASS}>
            {source === "literal" ? "Text" : source === "attribute" ? "Attribute" : "Field"}
          </label>
          {source === "literal" ? (
            <input
              id={`${component}-${index}-key`}
              {...register(`${component}.${index}.value`)}
              className={FIELD_CLASS}
            />
          ) : (
            <select
              id={`${component}-${index}-key`}
              {...register(`${component}.${index}.key`)}
              className={FIELD_CLASS}
            >
              <option value="">Choose…</option>
              {(source === "attribute" ? attributeKeys : MAPPABLE_FIELDS).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          )}
          {fieldError?.key || fieldError?.value ? (
            <p className="text-xs text-danger">
              {fieldError.key?.message ?? fieldError.value?.message}
            </p>
          ) : null}
        </div>

        <div>
          <label htmlFor={`${component}-${index}-fallback`} className={LABEL_CLASS}>
            Fallback
          </label>
          <input
            id={`${component}-${index}-fallback`}
            placeholder="e.g. there"
            {...register(`${component}.${index}.fallback`)}
            className={FIELD_CLASS}
          />
        </div>
      </div>
    </div>
  );
}
