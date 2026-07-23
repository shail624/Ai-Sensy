import { useMemo, useState } from "react";
import { useWatch, type UseFormReturn } from "react-hook-form";

import { EmptyState, ErrorState, Spinner, TagChip } from "@/components/ui";
import { apiErrorMessage, useSegments, useTags } from "@/features/campaigns/api";
import type { CampaignFormValues } from "@/features/campaigns/campaignForm";
import { SELECTABLE_AUDIENCE_TYPES } from "@/features/campaigns/campaignForm";
import { formatCount } from "@/features/campaigns/format";
import { AUDIENCE_TYPE_LABELS } from "@/features/campaigns/types";
import { buildRules, emptyFilters, useContactSearch } from "@/features/contacts";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";

interface Props {
  form: UseFormReturn<CampaignFormValues>;
}

/**
 * Step 2 — who receives it (FR-CAM-01).
 *
 * Opted-out contacts are removed by the server when the roster is materialized (FR-CAM-02), and the
 * review step reports how many that was; nothing here has to model compliance itself.
 */
export function CampaignAudienceStep({ form }: Props): JSX.Element {
  const { control, register, setValue, formState } = form;
  const audienceType = useWatch({ control, name: "audience_type" });
  const tagIds = useWatch({ control, name: "tag_ids" }) ?? [];
  const contactIds = useWatch({ control, name: "contact_ids" }) ?? [];
  const errors = formState.errors;

  const segments = useSegments(audienceType === "segment");
  const tags = useTags(audienceType === "tag");

  return (
    <div className="space-y-4">
      <fieldset>
        <legend className={LABEL_CLASS}>Audience</legend>
        <div className="mt-2 flex flex-wrap gap-2">
          {SELECTABLE_AUDIENCE_TYPES.map((type) => (
            <label
              key={type}
              className={`cursor-pointer rounded-md border px-3 py-1 text-sm ${
                audienceType === type
                  ? "border-accent text-accent"
                  : "border-border text-text-secondary hover:bg-hover"
              }`}
            >
              <input
                type="radio"
                value={type}
                {...register("audience_type")}
                className="sr-only"
              />
              {AUDIENCE_TYPE_LABELS[type]}
            </label>
          ))}
        </div>
        <p className="mt-2 text-xs text-text-disabled">
          To send to a list from a spreadsheet, import it into Contacts first, then target it by tag
          or segment.
        </p>
      </fieldset>

      {audienceType === "segment" ? (
        <div>
          <label htmlFor="campaign-segment" className={LABEL_CLASS}>
            Segment
          </label>
          {segments.isLoading ? (
            <Spinner label="Loading segments…" />
          ) : segments.isError ? (
            <ErrorState
              message={apiErrorMessage(segments.error)}
              onRetry={() => void segments.refetch()}
            />
          ) : (
            <>
              <select id="campaign-segment" {...register("segment_id")} className={FIELD_CLASS}>
                <option value="">Choose a segment…</option>
                {(segments.data ?? []).map((segment) => (
                  <option key={segment.id} value={segment.id}>
                    {segment.name}
                    {segment.cached_count !== null && segment.cached_count !== undefined
                      ? ` — ${formatCount(segment.cached_count)} contacts`
                      : ""}
                  </option>
                ))}
              </select>
              {(segments.data ?? []).length === 0 ? (
                <p className="mt-1 text-xs text-text-disabled">No segments have been created yet.</p>
              ) : null}
            </>
          )}
          {errors.segment_id ? (
            <p className="text-xs text-danger">{errors.segment_id.message}</p>
          ) : null}
        </div>
      ) : null}

      {audienceType === "tag" ? (
        <div>
          <p className={LABEL_CLASS}>Tags</p>
          {tags.isLoading ? (
            <Spinner label="Loading tags…" />
          ) : tags.isError ? (
            <ErrorState message={apiErrorMessage(tags.error)} onRetry={() => void tags.refetch()} />
          ) : (tags.data ?? []).length === 0 ? (
            <EmptyState title="No tags yet" description="Tag some contacts first." />
          ) : (
            <div className="mt-2 flex flex-wrap gap-2">
              {(tags.data ?? []).map((tag) => {
                const selected = tagIds.includes(tag.id);
                return (
                  <button
                    key={tag.id}
                    type="button"
                    aria-pressed={selected}
                    onClick={() =>
                      setValue(
                        "tag_ids",
                        selected ? tagIds.filter((id) => id !== tag.id) : [...tagIds, tag.id],
                        { shouldValidate: true },
                      )
                    }
                    className={`rounded-full border px-3 py-1 text-xs ${
                      selected
                        ? "border-accent text-accent"
                        : "border-border text-text-secondary hover:bg-hover"
                    }`}
                  >
                    {tag.name}
                    {tag.usage_count ? ` (${formatCount(tag.usage_count)})` : ""}
                  </button>
                );
              })}
            </div>
          )}
          {errors.tag_ids ? <p className="text-xs text-danger">{errors.tag_ids.message}</p> : null}
          <p className="mt-2 text-xs text-text-disabled">
            A contact carrying any of the selected tags is included.
          </p>
        </div>
      ) : null}

      {audienceType === "list" ? (
        <ContactPicker
          selected={contactIds}
          onChange={(next) => setValue("contact_ids", next, { shouldValidate: true })}
          error={errors.contact_ids?.message}
        />
      ) : null}
    </div>
  );
}

interface PickerProps {
  selected: string[];
  onChange: (next: string[]) => void;
  error?: string;
}

/**
 * Search-and-select over the contact list, using the shared contact search — one implementation of
 * contact search in the app, not a second one grown inside campaigns.
 */
function ContactPicker({ selected, onChange, error }: PickerProps): JSX.Element {
  const [search, setSearch] = useState("");
  const rules = useMemo(
    () => buildRules({ ...emptyFilters, search }, [], []),
    [search],
  );
  const contacts = useContactSearch({ rules, cursor: null, limit: 25 });
  const rows = contacts.data?.data ?? [];

  return (
    <div>
      <label htmlFor="campaign-contact-search" className={LABEL_CLASS}>
        Contacts
      </label>
      <input
        id="campaign-contact-search"
        type="search"
        value={search}
        onChange={(event) => setSearch(event.target.value)}
        placeholder="Search by name or phone…"
        className={FIELD_CLASS}
      />

      {selected.length > 0 ? (
        <div className="mt-2 flex flex-wrap gap-1">
          <span className="text-xs text-text-secondary">{selected.length} selected:</span>
          {selected.map((id) => (
            <TagChip
              key={id}
              name={id.slice(0, 8)}
              onRemove={() => onChange(selected.filter((entry) => entry !== id))}
            />
          ))}
        </div>
      ) : null}

      <div className="mt-2 max-h-64 overflow-y-auto rounded-md border border-border">
        {contacts.isLoading ? (
          <div className="p-3">
            <Spinner label="Searching…" />
          </div>
        ) : contacts.isError ? (
          <div className="p-3">
            <ErrorState
              message={apiErrorMessage(contacts.error)}
              onRetry={() => void contacts.refetch()}
            />
          </div>
        ) : rows.length === 0 ? (
          <EmptyState title="No contacts match" description="Try a different name or number." />
        ) : (
          <ul>
            {rows.map((contact) => {
              const isSelected = selected.includes(contact.id);
              return (
                <li key={contact.id} className="border-b border-border last:border-0">
                  <label className="flex cursor-pointer items-center gap-2 px-3 py-2 text-sm hover:bg-hover">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() =>
                        onChange(
                          isSelected
                            ? selected.filter((entry) => entry !== contact.id)
                            : [...selected, contact.id],
                        )
                      }
                    />
                    <span className="text-text-primary">{contact.full_name ?? "Unnamed"}</span>
                    <span className="text-text-secondary">{contact.phone_e164}</span>
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      {error ? <p className="text-xs text-danger">{error}</p> : null}
    </div>
  );
}
