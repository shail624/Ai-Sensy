import { EmptyState } from "@/components/ui";
import { groupRules } from "@/features/segments/selectors";
import type { AttributeDefinition, FieldSource, MatchType, SegmentRule } from "@/features/segments/types";
import {
  fieldsForSource,
  MATCH_TYPE_EXPLANATIONS,
  operatorLabel,
  shapeFor,
} from "@/features/segments/types";

/** A stored value rendered the way the rule reads it. */
function describeValue(rule: SegmentRule): string {
  const shape = shapeFor(rule.operator);
  if (shape === "boolean") return rule.value === true ? "yes" : "no";
  if (shape === "range") {
    return Array.isArray(rule.value) ? rule.value.map(String).join(" and ") : "—";
  }
  if (shape === "list") {
    return Array.isArray(rule.value) ? rule.value.map(String).join(", ") : "—";
  }
  if (rule.value === null || rule.value === undefined || rule.value === "") return "—";
  return String(rule.value);
}

interface Props {
  rules: SegmentRule[];
  matchType: string;
  attributes: AttributeDefinition[];
}

/**
 * The rule tree, read back as a sentence.
 *
 * Rules sharing a `group_index` are ANDed and the groups combined by `match_type`, so the summary
 * shows two levels — conditions inside a group joined by "and", groups joined by "and"/"or"
 * according to the match type. A flat list of rules would not convey which is which.
 */
export function RuleSummary({ rules, matchType, attributes }: Props): JSX.Element {
  const groups = groupRules(rules);
  const joiner = matchType === "any" ? "OR" : "AND";

  if (groups.length === 0) {
    return (
      <EmptyState
        title="No conditions"
        description="A segment with no conditions matches every contact in the organization."
      />
    );
  }

  return (
    <div>
      <p className="mb-3 text-sm text-text-secondary">
        {MATCH_TYPE_EXPLANATIONS[matchType as MatchType] ?? ""}
      </p>

      <ol className="space-y-2">
        {groups.map((group, index) => (
          <li key={group.index}>
            {index > 0 ? (
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-accent">
                {joiner}
              </p>
            ) : null}
            <div className="rounded-md border border-border p-3">
              <ul className="space-y-1">
                {group.rules.map((rule, ruleIndex) => {
                  const source = rule.field_source as FieldSource;
                  const field = fieldsForSource(source, attributes).find(
                    (candidate) => candidate.key === rule.field_key,
                  );
                  const kind = field?.kind ?? "string";

                  return (
                    <li key={`${rule.field_key}-${ruleIndex}`} className="text-sm">
                      {ruleIndex > 0 ? (
                        <span className="mr-2 text-xs font-semibold uppercase text-text-disabled">
                          and
                        </span>
                      ) : null}
                      <span className="text-text-primary">
                        {source === "tag" ? "Tag" : (field?.label ?? rule.field_key)}
                      </span>{" "}
                      <span className="text-text-secondary">
                        {operatorLabel(rule.operator, kind)}
                      </span>{" "}
                      <span className="font-medium text-text-primary">{describeValue(rule)}</span>
                    </li>
                  );
                })}
              </ul>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
