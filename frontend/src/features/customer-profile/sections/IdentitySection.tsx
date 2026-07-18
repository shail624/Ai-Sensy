import { DefinitionRow, Section } from "@/components/ui";
import type { Contact } from "@/features/customer-profile/types";

function displayName(contact: Contact): string {
  if (contact.full_name) return contact.full_name;
  const composed = [contact.first_name, contact.last_name].filter(Boolean).join(" ");
  if (composed) return composed;
  return contact.profile_name ?? "Unknown contact";
}

/** Identity: name, phone, WhatsApp number, opt-in (Doc 05 B4 profile). */
export function IdentitySection({ contact }: { contact: Contact }): JSX.Element {
  return (
    <Section title="Basic information">
      <dl>
        <DefinitionRow label="Name">{displayName(contact)}</DefinitionRow>
        <DefinitionRow label="Phone">{contact.phone_e164}</DefinitionRow>
        <DefinitionRow label="WhatsApp number">{contact.wa_id}</DefinitionRow>
        {contact.email ? <DefinitionRow label="Email">{contact.email}</DefinitionRow> : null}
        <DefinitionRow label="Opt-in">{contact.opt_in_status}</DefinitionRow>
      </dl>
    </Section>
  );
}
