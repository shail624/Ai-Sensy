import { Check, Tag, UserRoundCheck, UsersRound } from "lucide-react";
import { useMemo, useState } from "react";
import { useWatch, type UseFormReturn } from "react-hook-form";
import { Link } from "react-router-dom";

import { EmptyState, ErrorState, Spinner, TagChip } from "@/components/ui";
import { apiErrorMessage, useSegments, useTags } from "@/features/campaigns/api";
import type { CampaignFormValues } from "@/features/campaigns/campaignForm";
import { SELECTABLE_AUDIENCE_TYPES } from "@/features/campaigns/campaignForm";
import { formatCount } from "@/features/campaigns/format";
import { AUDIENCE_TYPE_LABELS } from "@/features/campaigns/types";
import { buildRules, emptyFilters, useContactSearch } from "@/features/contacts";
import {
  audiencePresetById,
  audiencePresetIdForSegment,
} from "@/features/segments/audiencePresets";

const FIELD_CLASS =
  "min-h-11 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none transition focus:border-accent focus:ring-2 focus:ring-accent-soft";
const LABEL_CLASS = "mb-1.5 block text-sm font-semibold text-text-primary";

const AUDIENCE_META = {
  segment: {
    description: "Use a saved, dynamic audience",
    icon: UsersRound,
  },
  tag: {
    description: "Reach contacts carrying selected tags",
    icon: Tag,
  },
  list: {
    description: "Choose specific contacts directly",
    icon: UserRoundCheck,
  },
} as const;

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
  const segmentId = useWatch({ control, name: "segment_id" });
  const tagIds = useWatch({ control, name: "tag_ids" }) ?? [];
  const contactIds = useWatch({ control, name: "contact_ids" }) ?? [];
  const errors = formState.errors;

  const segments = useSegments(audienceType === "segment");
  const tags = useTags(audienceType === "tag");
  const quickSegments = useMemo(
    () =>
      (segments.data ?? [])
        .map((segment) => {
          const presetId = audiencePresetIdForSegment(segment);
          return presetId ? { segment, preset: audiencePresetById(presetId) } : null;
        })
        .filter((entry): entry is NonNullable<typeof entry> => entry !== null)
        .slice(0, 4),
    [segments.data],
  );

  return (
    <div className="space-y-4">
      <fieldset>
        <legend className="sr-only">Audience source</legend>
        <div className="grid gap-3 sm:grid-cols-3">
          {SELECTABLE_AUDIENCE_TYPES.map((type) => {
            const meta = AUDIENCE_META[type as keyof typeof AUDIENCE_META];
            const Icon = meta.icon;
            const selected = audienceType === type;

            return (
              <label
                key={type}
                className={`relative flex min-h-24 cursor-pointer items-start gap-3 rounded-xl border p-4 transition-colors ${
                  selected
                    ? "border-accent bg-accent-soft ring-1 ring-accent"
                    : "border-border bg-surface hover:bg-hover"
                }`}
              >
                <input
                  type="radio"
                  value={type}
                  {...register("audience_type")}
                  className="sr-only"
                />
                <span
                  className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${
                    selected ? "bg-surface text-accent" : "bg-surface-subtle text-text-secondary"
                  }`}
                >
                  <Icon aria-hidden className="h-4 w-4" />
                </span>
                <span className="min-w-0">
                  <span className="block text-sm font-semibold text-text-primary">
                    {AUDIENCE_TYPE_LABELS[type]}
                  </span>
                  <span className="mt-1 block text-xs leading-relaxed text-text-secondary">
                    {meta.description}
                  </span>
                </span>
                {selected ? (
                  <span className="absolute right-2.5 top-2.5 flex h-5 w-5 items-center justify-center rounded-full bg-accent text-accent-fg">
                    <Check aria-hidden className="h-3 w-3" />
                  </span>
                ) : null}
              </label>
            );
          })}
        </div>
      </fieldset>

      <div className="flex items-start gap-2 rounded-lg bg-success-soft px-3 py-2.5 text-xs leading-relaxed text-success-on-soft">
        <UserRoundCheck aria-hidden className="mt-0.5 h-4 w-4 shrink-0" />
        <p>
          Opt-in protection stays on. Spreadsheet lists are imported into Contacts first, then
          targeted safely by segment or tag.
        </p>
      </div>

      {audienceType === "segment" ? (
        <div className="rounded-xl border border-border bg-surface-subtle p-4">
          {quickSegments.length > 0 ? (
            <div className="mb-4">
              <p className={LABEL_CLASS}>Quick audiences</p>
              <div className="grid gap-2 sm:grid-cols-2">
                {quickSegments.map(({ segment, preset }) => {
                  const selected = segment.id === segmentId;
                  return (
                    <button
                      key={segment.id}
                      type="button"
                      aria-pressed={selected}
                      onClick={() =>
                        setValue("segment_id", segment.id, {
                          shouldDirty: true,
                          shouldValidate: true,
                        })
                      }
                      className={`flex min-h-14 items-center justify-between gap-3 rounded-lg border px-3 py-2 text-left transition ${
                        selected
                          ? "border-accent bg-accent-soft ring-1 ring-accent"
                          : "border-border bg-surface hover:bg-hover"
                      }`}
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-sm font-semibold text-text-primary">
                          {segment.name}
                        </span>
                        <span className="block text-xs text-text-secondary">
                          {preset.shortLabel}
                          {segment.cached_count !== null && segment.cached_count !== undefined
                            ? ` · ${formatCount(segment.cached_count)} contacts`
                            : " · Not evaluated"}
                        </span>
                      </span>
                      {selected ? (
                        <Check aria-hidden className="h-4 w-4 shrink-0 text-accent" />
                      ) : null}
                    </button>
                  );
                })}
              </div>
              <p className="mt-2 text-xs text-text-disabled">
                These are saved segments. Their rules are still resolved live when the campaign runs.
              </p>
            </div>
          ) : null}
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
                <p className="mt-1 text-xs text-text-disabled">
                  No segments have been created yet. Open{" "}
                  <Link
                    to="/segments"
                    target="_blank"
                    rel="noreferrer"
                    className="font-semibold text-accent hover:underline"
                  >
                    audience presets
                  </Link>{" "}
                  to create one in a new tab.
                </p>
              ) : null}
            </>
          )}
          {errors.segment_id ? (
            <p className="text-xs text-danger">{errors.segment_id.message}</p>
          ) : null}
        </div>
      ) : null}

      {audienceType === "tag" ? (
        <div className="rounded-xl border border-border bg-surface-subtle p-4">
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
                    className={`min-h-9 rounded-full border px-3 py-1 text-xs font-medium ${
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
    <div className="rounded-xl border border-border bg-surface-subtle p-4">
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

      <div className="mt-3 max-h-64 overflow-y-auto rounded-lg border border-border bg-surface">
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
                  <label className="flex min-h-11 cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-hover">
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
