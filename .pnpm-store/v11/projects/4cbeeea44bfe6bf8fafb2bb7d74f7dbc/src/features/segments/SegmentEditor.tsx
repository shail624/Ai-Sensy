import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useAttributeDefinitions,
  useCreateSegment,
  useTags,
  useUpdateSegment,
} from "@/features/segments/api";
import { RuleBuilder } from "@/features/segments/RuleBuilder";
import { RuleSummary } from "@/features/segments/RuleSummary";
import type { SegmentSeed } from "@/features/segments/audiencePresets";
import type { RuleGroup } from "@/features/segments/selectors";
import {
  flattenGroups,
  groupRules,
  hasProblems,
  validateSegment,
} from "@/features/segments/selectors";
import type { MatchType, Segment } from "@/features/segments/types";
import {
  MATCH_TYPE_EXPLANATIONS,
  MATCH_TYPE_LABELS,
  MATCH_TYPES,
  MAX_DESCRIPTION_LENGTH,
  MAX_NAME_LENGTH,
} from "@/features/segments/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";
const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50";

interface Props {
  /** Absent → create a new segment; present → edit that one. */
  segment?: Segment;
  /**
   * Starting values without identity — how a duplicate opens prefilled from another segment while
   * still creating a new one. Ignored when `segment` is present, which supplies its own.
   */
  initial?: SegmentSeed;
}

/**
 * Create or edit a segment.
 *
 * Editing replaces the rule set wholesale — the PATCH carries the complete list and the server
 * rebuilds the rows from it — so the builder always holds the whole tree rather than a diff.
 *
 * Saving rules **invalidates the segment's cached size** server-side, which is stated before the
 * save rather than discovered as a count that silently became "not evaluated".
 */
export function SegmentEditor({ segment, initial }: Props): JSX.Element {
  const navigate = useNavigate();
  const editing = segment !== undefined;
  const seed = segment ?? initial;

  const attributes = useAttributeDefinitions();
  const tags = useTags();
  const create = useCreateSegment();
  const update = useUpdateSegment();

  const [name, setName] = useState(seed?.name ?? "");
  const [description, setDescription] = useState(seed?.description ?? "");
  const [matchType, setMatchType] = useState<MatchType>((seed?.match_type as MatchType) ?? "all");
  const [groups, setGroups] = useState<RuleGroup[]>(() => groupRules(seed?.rules ?? []));
  const [showErrors, setShowErrors] = useState(false);

  const definitions = useMemo(() => attributes.data ?? [], [attributes.data]);
  const problems = useMemo(
    () => validateSegment(name, description, groups, definitions),
    [name, description, groups, definitions],
  );
  const visible = showErrors ? problems : { rules: {} };

  const pending = create.isPending || update.isPending;
  const error = create.error ?? update.error;
  const flat = useMemo(() => flattenGroups(groups), [groups]);

  const rulesChanged =
    editing && JSON.stringify(flat) !== JSON.stringify(segment.rules);
  const matchChanged = editing && matchType !== segment.match_type;

  function submit(): void {
    setShowErrors(true);
    if (hasProblems(problems)) return;

    const body = {
      name: name.trim(),
      description: description.trim() || null,
      match_type: matchType,
      rules: flat,
    };

    if (editing) {
      update.mutate(
        { segmentId: segment.id, body },
        { onSuccess: (saved) => navigate(`/segments/${saved.id}`) },
      );
      return;
    }
    create.mutate(body, { onSuccess: (saved) => navigate(`/segments/${saved.id}`) });
  }

  if (attributes.isLoading || tags.isLoading) return <Spinner label="Loading fields…" />;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="space-y-4">
        <Section title="Identity">
          <div className="space-y-3">
            <div>
              <label htmlFor="segment-name" className={LABEL_CLASS}>
                Name
              </label>
              <input
                id="segment-name"
                value={name}
                maxLength={MAX_NAME_LENGTH}
                onChange={(event) => setName(event.target.value)}
                placeholder="Lapsed customers — Mumbai"
                className={FIELD_CLASS}
              />
              <p className="mt-1 text-xs text-text-disabled">
                {name.length}/{MAX_NAME_LENGTH} · must be unique in this organization
              </p>
              {visible.name ? <p className="text-xs text-danger">{visible.name}</p> : null}
            </div>

            <div>
              <label htmlFor="segment-description" className={LABEL_CLASS}>
                Description
              </label>
              <textarea
                id="segment-description"
                rows={2}
                maxLength={MAX_DESCRIPTION_LENGTH}
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Who this segment is for, in one line."
                className={FIELD_CLASS}
              />
              <p className="mt-1 text-xs text-text-disabled">
                {description.length}/{MAX_DESCRIPTION_LENGTH}
              </p>
              {visible.description ? (
                <p className="text-xs text-danger">{visible.description}</p>
              ) : null}
            </div>
          </div>
        </Section>

        <Section title="Conditions">
          <div className="mb-3">
            <label htmlFor="segment-match" className={LABEL_CLASS}>
              How groups combine
            </label>
            <select
              id="segment-match"
              value={matchType}
              onChange={(event) => setMatchType(event.target.value as MatchType)}
              className={FIELD_CLASS}
            >
              {MATCH_TYPES.map((option) => (
                <option key={option} value={option}>
                  {MATCH_TYPE_LABELS[option]}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-text-disabled">
              {MATCH_TYPE_EXPLANATIONS[matchType]}
            </p>
          </div>

          <RuleBuilder
            groups={groups}
            onChange={setGroups}
            attributes={definitions}
            tags={tags.data ?? []}
            matchType={matchType}
            problems={visible.rules}
          />
        </Section>
      </div>

      <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
        <Section title="Summary">
          <RuleSummary rules={flat} matchType={matchType} attributes={definitions} />
        </Section>

        {editing && (rulesChanged || matchChanged) ? (
          <p className="rounded-md border border-warning px-3 py-2 text-sm text-warning">
            Changing the conditions clears this segment&apos;s saved size. It will read as “not
            evaluated” until you refresh it.
          </p>
        ) : null}

        {flat.length === 0 ? (
          <p className="rounded-md border border-warning px-3 py-2 text-sm text-warning">
            With no conditions this segment matches <strong>every contact</strong> in the
            organization.
          </p>
        ) : null}

        {error ? <ErrorState message={apiErrorMessage(error)} /> : null}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <button
            type="button"
            className={BUTTON_CLASS}
            onClick={() => navigate(editing ? `/segments/${segment.id}` : "/segments")}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={submit}
            disabled={pending}
            className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg disabled:opacity-50"
          >
            {pending ? "Saving…" : editing ? "Save segment" : "Create segment"}
          </button>
        </div>

        <p className="text-xs text-text-disabled">
          Conditions are validated against the contact model when you save; anything the platform
          cannot evaluate is refused with an explanation.
        </p>
      </div>
    </div>
  );
}
