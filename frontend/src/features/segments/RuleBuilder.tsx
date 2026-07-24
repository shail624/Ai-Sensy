import type { RuleGroup } from "@/features/segments/selectors";
import type {
  AttributeDefinition,
  FieldSource,
  FieldSpec,
  SegmentRule,
  Tag,
  ValueKind,
} from "@/features/segments/types";
import {
  FIELD_SOURCE_HINTS,
  FIELD_SOURCE_LABELS,
  FIELD_SOURCES,
  fieldsForSource,
  operatorLabel,
  operatorsFor,
  shapeFor,
} from "@/features/segments/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const SMALL_BUTTON =
  "rounded-md border border-border px-2 py-1 text-xs text-text-primary hover:bg-hover disabled:opacity-50";

/** A `datetime-local` control works in local time; the compiler parses ISO-8601. */
function toLocalInput(value: unknown): string {
  if (typeof value !== "string" || value === "") return "";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "";
  return new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

function fromLocalInput(local: string): string {
  return local ? new Date(local).toISOString() : "";
}

/** A fresh rule for a source, defaulted to the first field and operator that source allows. */
export function blankRule(source: FieldSource, attributes: AttributeDefinition[]): SegmentRule {
  const fields = fieldsForSource(source, attributes);
  const field = fields[0];
  const kind = field?.kind ?? "string";
  const operator = operatorsFor(source, kind)[0] ?? "eq";
  return {
    group_index: 0,
    field_source: source,
    field_key: field?.key ?? "",
    operator,
    value: defaultValueFor(operator),
  };
}

/** The empty value a shape expects, so a rule is never born in a state its operator rejects. */
export function defaultValueFor(operator: string): SegmentRule["value"] {
  const shape = shapeFor(operator);
  if (shape === "boolean") return true;
  if (shape === "range") return ["", ""];
  if (shape === "list") return [];
  return "";
}

interface Props {
  groups: RuleGroup[];
  onChange: (next: RuleGroup[]) => void;
  attributes: AttributeDefinition[];
  tags: Tag[];
  matchType: string;
  /** Keyed `"<groupIndex>:<ruleIndex>"`, from `validateSegment`. */
  problems: Record<string, string>;
}

/**
 * The segment rule builder.
 *
 * It mirrors the compiler's two-level model exactly: conditions inside a group are ANDed, and the
 * groups are combined by the segment's match type. Nothing else is expressible — the compiler has
 * no deeper nesting — so the builder offers none.
 *
 * Every control is constrained to what the compiler will accept: the field list comes from the
 * source, the operator list from the field's type, and the value control from the operator's shape.
 * A rule that cannot be built here is a rule the server would answer 422 for.
 */
export function RuleBuilder({
  groups,
  onChange,
  attributes,
  tags,
  matchType,
  problems,
}: Props): JSX.Element {
  const joiner = matchType === "any" ? "OR" : "AND";

  function updateRule(groupIndex: number, ruleIndex: number, patch: Partial<SegmentRule>): void {
    onChange(
      groups.map((group, gi) =>
        gi !== groupIndex
          ? group
          : {
              ...group,
              rules: group.rules.map((rule, ri) =>
                ri === ruleIndex ? { ...rule, ...patch } : rule,
              ),
            },
      ),
    );
  }

  function removeRule(groupIndex: number, ruleIndex: number): void {
    onChange(
      groups
        .map((group, gi) =>
          gi !== groupIndex
            ? group
            : { ...group, rules: group.rules.filter((_, ri) => ri !== ruleIndex) },
        )
        // A group with no conditions has no meaning, so it goes with its last rule.
        .filter((group) => group.rules.length > 0),
    );
  }

  function addRule(groupIndex: number): void {
    onChange(
      groups.map((group, gi) =>
        gi !== groupIndex
          ? group
          : { ...group, rules: [...group.rules, blankRule("contact", attributes)] },
      ),
    );
  }

  function addGroup(): void {
    onChange([
      ...groups,
      { index: groups.length, rules: [blankRule("contact", attributes)] },
    ]);
  }

  return (
    <div className="space-y-3">
      {groups.length === 0 ? (
        <div className="rounded-md border border-dashed border-border p-4 text-center">
          <p className="text-sm text-text-secondary">No conditions yet.</p>
          <p className="mt-1 text-xs text-warning">
            A segment with no conditions matches every contact in the organization.
          </p>
        </div>
      ) : null}

      {groups.map((group, groupIndex) => (
        <div key={group.index}>
          {groupIndex > 0 ? (
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-accent">
              {joiner}
            </p>
          ) : null}

          <div className="rounded-md border border-border p-3">
            <div className="space-y-3">
              {group.rules.map((rule, ruleIndex) => (
                <RuleRow
                  key={`${groupIndex}-${ruleIndex}`}
                  rule={rule}
                  first={ruleIndex === 0}
                  id={`${groupIndex}-${ruleIndex}`}
                  problem={problems[`${groupIndex}:${ruleIndex}`]}
                  attributes={attributes}
                  tags={tags}
                  onChange={(patch) => updateRule(groupIndex, ruleIndex, patch)}
                  onRemove={() => removeRule(groupIndex, ruleIndex)}
                />
              ))}
            </div>

            <button
              type="button"
              onClick={() => addRule(groupIndex)}
              className={`${SMALL_BUTTON} mt-3`}
            >
              Add condition
            </button>
          </div>
        </div>
      ))}

      <button type="button" onClick={addGroup} className={SMALL_BUTTON}>
        {groups.length === 0 ? "Add a condition" : `Add ${joiner} group`}
      </button>
    </div>
  );
}

interface RowProps {
  rule: SegmentRule;
  first: boolean;
  id: string;
  problem?: string;
  attributes: AttributeDefinition[];
  tags: Tag[];
  onChange: (patch: Partial<SegmentRule>) => void;
  onRemove: () => void;
}

function RuleRow({
  rule,
  first,
  id,
  problem,
  attributes,
  tags,
  onChange,
  onRemove,
}: RowProps): JSX.Element {
  const source = rule.field_source as FieldSource;
  const fields = fieldsForSource(source, attributes);
  const field = fields.find((candidate) => candidate.key === rule.field_key);
  const kind: ValueKind = field?.kind ?? "string";
  const operators = operatorsFor(source, kind);

  /** Changing the source resets the field, operator and value: none of them carries across. */
  function changeSource(next: FieldSource): void {
    onChange(blankRule(next, attributes));
  }

  /** Changing the field can invalidate the operator, which can invalidate the value. */
  function changeField(nextKey: string): void {
    const nextField = fields.find((candidate) => candidate.key === nextKey);
    const nextKind = nextField?.kind ?? "string";
    const allowed = operatorsFor(source, nextKind);
    const operator = allowed.includes(rule.operator) ? rule.operator : (allowed[0] ?? "eq");
    onChange({
      field_key: nextKey,
      operator,
      value: operator === rule.operator ? rule.value : defaultValueFor(operator),
    });
  }

  function changeOperator(next: string): void {
    // The value only survives when the shape does; otherwise it would be sent in a form the
    // compiler rejects.
    const keep = shapeFor(next) === shapeFor(rule.operator);
    onChange({ operator: next, value: keep ? rule.value : defaultValueFor(next) });
  }

  return (
    <div className="rounded-md border border-border bg-surface-2 p-2">
      {!first ? (
        <p className="mb-1 text-xs font-semibold uppercase text-text-disabled">and</p>
      ) : null}

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-4">
        <div>
          <label htmlFor={`rule-${id}-source`} className="text-xs font-medium text-text-secondary">
            Source
          </label>
          <select
            id={`rule-${id}-source`}
            value={source}
            onChange={(event) => changeSource(event.target.value as FieldSource)}
            className={FIELD_CLASS}
          >
            {FIELD_SOURCES.map((option) => (
              <option key={option} value={option}>
                {FIELD_SOURCE_LABELS[option]}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor={`rule-${id}-field`} className="text-xs font-medium text-text-secondary">
            Field
          </label>
          {source === "tag" ? (
            <p className={`${FIELD_CLASS} opacity-60`}>Tags</p>
          ) : (
            <select
              id={`rule-${id}-field`}
              value={rule.field_key}
              onChange={(event) => changeField(event.target.value)}
              className={FIELD_CLASS}
            >
              {fields.length === 0 ? <option value="">No fields available</option> : null}
              {fields.map((option) => (
                <option key={option.key} value={option.key}>
                  {option.label}
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label
            htmlFor={`rule-${id}-operator`}
            className="text-xs font-medium text-text-secondary"
          >
            Condition
          </label>
          <select
            id={`rule-${id}-operator`}
            value={rule.operator}
            onChange={(event) => changeOperator(event.target.value)}
            className={FIELD_CLASS}
          >
            {operators.map((option) => (
              <option key={option} value={option}>
                {operatorLabel(option, kind)}
              </option>
            ))}
          </select>
        </div>

        <div>
          <RuleValue
            id={id}
            rule={rule}
            field={field}
            kind={kind}
            source={source}
            tags={tags}
            onChange={onChange}
          />
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between gap-2">
        <p className="text-xs text-text-disabled">{FIELD_SOURCE_HINTS[source]}</p>
        <button type="button" onClick={onRemove} className="rounded px-2 text-xs text-danger hover:bg-hover">
          Remove
        </button>
      </div>

      {problem ? <p className="mt-1 text-xs text-danger">{problem}</p> : null}
    </div>
  );
}

interface ValueProps {
  id: string;
  rule: SegmentRule;
  field: FieldSpec | undefined;
  kind: ValueKind;
  source: FieldSource;
  tags: Tag[];
  onChange: (patch: Partial<SegmentRule>) => void;
}

/** The control for a rule's value, chosen by the operator's shape and the field's type. */
function RuleValue({ id, rule, field, kind, source, tags, onChange }: ValueProps): JSX.Element {
  const shape = shapeFor(rule.operator);
  const label = <label htmlFor={`rule-${id}-value`} className="text-xs font-medium text-text-secondary">Value</label>;

  if (shape === "boolean") {
    return (
      <>
        {label}
        <select
          id={`rule-${id}-value`}
          value={rule.value === true ? "true" : "false"}
          onChange={(event) => onChange({ value: event.target.value === "true" })}
          className={FIELD_CLASS}
        >
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      </>
    );
  }

  if (shape === "range") {
    const pair = Array.isArray(rule.value) ? rule.value : ["", ""];
    const inputType = kind === "datetime" ? "datetime-local" : "number";
    const read = (index: number) =>
      kind === "datetime" ? toLocalInput(pair[index]) : String(pair[index] ?? "");
    const write = (index: number, raw: string) => {
      const next = [...pair];
      next[index] = kind === "datetime" ? fromLocalInput(raw) : raw;
      onChange({ value: next });
    };

    return (
      <>
        {label}
        <div className="flex gap-1">
          <input
            id={`rule-${id}-value`}
            type={inputType}
            aria-label="From"
            value={read(0)}
            onChange={(event) => write(0, event.target.value)}
            className={FIELD_CLASS}
          />
          <input
            type={inputType}
            aria-label="To"
            value={read(1)}
            onChange={(event) => write(1, event.target.value)}
            className={FIELD_CLASS}
          />
        </div>
      </>
    );
  }

  if (shape === "list") {
    const list = Array.isArray(rule.value) ? rule.value : [];
    // Tags and enums have a known vocabulary, so a multi-select beats free text; everything else
    // is comma-separated because the compiler accepts any list of scalars.
    const choices =
      source === "tag"
        ? tags.map((tag) => ({ value: tag.name, label: tag.name }))
        : (field?.choices ?? []);

    if (choices.length > 0) {
      return (
        <>
          <p className="text-xs font-medium text-text-secondary">Values</p>
          <div className="mt-1 flex max-h-24 flex-wrap gap-1 overflow-y-auto">
            {choices.map((choice) => {
              const selected = list.includes(choice.value);
              return (
                <button
                  key={choice.value}
                  type="button"
                  aria-pressed={selected}
                  onClick={() =>
                    onChange({
                      value: selected
                        ? list.filter((entry) => entry !== choice.value)
                        : [...list, choice.value],
                    })
                  }
                  className={`rounded-full border px-2 py-0.5 text-xs ${
                    selected
                      ? "border-accent text-accent"
                      : "border-border text-text-secondary hover:bg-hover"
                  }`}
                >
                  {choice.label}
                </button>
              );
            })}
          </div>
        </>
      );
    }

    return (
      <>
        {label}
        <input
          id={`rule-${id}-value`}
          value={list.map(String).join(", ")}
          onChange={(event) =>
            onChange({
              value: event.target.value
                .split(",")
                .map((entry) => entry.trim())
                .filter((entry) => entry !== ""),
            })
          }
          placeholder="one, two, three"
          className={FIELD_CLASS}
        />
      </>
    );
  }

  // Single value.
  if (source === "tag") {
    return (
      <>
        {label}
        <select
          id={`rule-${id}-value`}
          value={typeof rule.value === "string" ? rule.value : ""}
          onChange={(event) => onChange({ value: event.target.value })}
          className={FIELD_CLASS}
        >
          <option value="">Choose a tag…</option>
          {tags.map((tag) => (
            <option key={tag.id} value={tag.name}>
              {tag.name}
            </option>
          ))}
        </select>
      </>
    );
  }

  if (field?.choices && field.choices.length > 0) {
    return (
      <>
        {label}
        <select
          id={`rule-${id}-value`}
          value={typeof rule.value === "string" ? rule.value : ""}
          onChange={(event) => onChange({ value: event.target.value })}
          className={FIELD_CLASS}
        >
          <option value="">Choose…</option>
          {field.choices.map((choice) => (
            <option key={choice.value} value={choice.value}>
              {choice.label}
            </option>
          ))}
        </select>
      </>
    );
  }

  if (kind === "datetime") {
    return (
      <>
        {label}
        <input
          id={`rule-${id}-value`}
          type="datetime-local"
          value={toLocalInput(rule.value)}
          onChange={(event) => onChange({ value: fromLocalInput(event.target.value) })}
          className={FIELD_CLASS}
        />
      </>
    );
  }

  return (
    <>
      {label}
      <input
        id={`rule-${id}-value`}
        type={kind === "number" ? "number" : "text"}
        value={rule.value === null || rule.value === undefined ? "" : String(rule.value)}
        onChange={(event) =>
          onChange({
            value: kind === "number" && event.target.value !== ""
              ? Number(event.target.value)
              : event.target.value,
          })
        }
        className={FIELD_CLASS}
      />
    </>
  );
}
