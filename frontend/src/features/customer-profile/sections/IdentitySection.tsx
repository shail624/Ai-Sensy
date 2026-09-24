import { DefinitionRow, Section } from "@/components/ui";
import type { Contact } from "@/features/customer-profile/types";
import { formatDay, saleStatusOption } from "@/features/inbox/saleStatus";

const OPT_IN_WORDS: Record<string, string> = { opted_in: "Yes", opted_out: "No", unknown: "Not asked yet" };

function displayName(contact: Contact): string {
  if (contact.full_name) return contact.full_name;
  const composed = [contact.first_name, contact.last_name].filter(Boolean).join(" ");
  if (composed) return composed;
  return contact.profile_name ?? "Unknown contact";
}

/** Identity: name, phone, WhatsApp number, opt-in (Doc 05 B4 profile). */
export function IdentitySection({ contact }: { contact: Contact }): JSX.Element {
  const sale = saleStatusOption(contact.sale_status);
  return (
    <Section title="Basic information">
      <dl>
        <DefinitionRow label="Name">{displayName(contact)}</DefinitionRow>
        <DefinitionRow label="Phone">{contact.phone_e164}</DefinitionRow>
        <DefinitionRow label="WhatsApp number">{contact.wa_id}</DefinitionRow>
        {contact.email ? <DefinitionRow label="Email">{contact.email}</DefinitionRow> : null}
        <DefinitionRow label="Opt-in">{OPT_IN_WORDS[contact.opt_in_status] ?? contact.opt_in_status}</DefinitionRow>
        <DefinitionRow label="Sale status">
          {sale ? <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${sale.pill}`}>{sale.label}</span> : "Not marked"}
        </DefinitionRow>
        <DefinitionRow label="Release date">{contact.release_date ? formatDay(contact.release_date) : "—"}</DefinitionRow>
      </dl>
    </Section>
  );
}
