import { DefinitionRow, EmptyState, Section } from "@/components/ui";
import type { AttributeDefinition, Contact } from "@/features/customer-profile/types";

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

interface Props {
  contact: Contact;
  definitions: AttributeDefinition[];
}

/**
 * Custom attributes, rendered generically from the org's attribute definitions (labels + values) —
 * so Vi Number, Circle, Reactivation Status, Customer Type/Outcome etc. all surface here once
 * defined, with no field names hard-coded.
 */
export function CustomAttributesSection({ contact, definitions }: Props): JSX.Element {
  const attributes = contact.attributes;
  const rows = definitions.filter((def) => attributes[def.key_name] !== undefined);

  return (
    <Section title="Custom attributes">
      {rows.length === 0 ? (
        <EmptyState
          title="No custom attributes set"
          description="Fields such as Vi Number, Circle and Reactivation Status appear here once defined and filled."
        />
      ) : (
        <dl>
          {rows.map((def) => (
            <DefinitionRow key={def.id} label={def.label}>
              {formatValue(attributes[def.key_name])}
            </DefinitionRow>
          ))}
        </dl>
      )}
    </Section>
  );
}
