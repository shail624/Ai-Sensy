import { Link, useNavigate } from "react-router-dom";

import { TagChip } from "@/components/ui";
import type { Contact } from "@/features/contacts/types";

function displayName(contact: Contact): string {
  return contact.full_name ?? contact.profile_name ?? contact.phone_e164;
}

function initials(contact: Contact): string {
  return displayName(contact).slice(0, 2).toUpperCase();
}

function reactivationValue(contact: Contact, key: string | null): string {
  if (!key) return "—";
  const value = contact.attributes[key];
  return value === undefined || value === null || value === "" ? "—" : String(value);
}

interface Props {
  contacts: Contact[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: () => void;
  /** Custom-attribute key to surface as a "Reactivation status" column, when one is defined. */
  reactivationKey: string | null;
}

export function ContactsTable({
  contacts,
  selectedIds,
  onToggle,
  onToggleAll,
  reactivationKey,
}: Props): JSX.Element {
  const navigate = useNavigate();
  const allSelected = contacts.length > 0 && contacts.every((contact) => selectedIds.has(contact.id));

  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
          <tr>
            <th scope="col" className="w-10 px-3 py-2">
              <input
                type="checkbox"
                aria-label="Select all contacts on this page"
                checked={allSelected}
                onChange={onToggleAll}
              />
            </th>
            <th scope="col" className="px-3 py-2">Name</th>
            <th scope="col" className="px-3 py-2">Phone</th>
            <th scope="col" className="px-3 py-2">Tags</th>
            {reactivationKey ? (
              <th scope="col" className="px-3 py-2">Reactivation status</th>
            ) : null}
            <th scope="col" className="px-3 py-2">Last updated</th>
          </tr>
        </thead>
        <tbody>
          {contacts.map((contact) => (
            <tr
              key={contact.id}
              onClick={() => navigate(`/contacts/${contact.id}`)}
              className="cursor-pointer border-b border-border last:border-0 hover:bg-hover"
            >
              <td className="px-3 py-2" onClick={(event) => event.stopPropagation()}>
                <input
                  type="checkbox"
                  aria-label={`Select ${displayName(contact)}`}
                  checked={selectedIds.has(contact.id)}
                  onChange={() => onToggle(contact.id)}
                />
              </td>
              <td className="px-3 py-2">
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-surface-2 text-xs font-medium text-text-secondary"
                  >
                    {initials(contact)}
                  </span>
                  <Link
                    to={`/contacts/${contact.id}`}
                    onClick={(event) => event.stopPropagation()}
                    className="font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  >
                    {displayName(contact)}
                  </Link>
                </div>
              </td>
              <td className="px-3 py-2 text-text-secondary">{contact.phone_e164}</td>
              <td className="px-3 py-2">
                <div className="flex flex-wrap gap-1">
                  {contact.tags.map((tag) => (
                    <TagChip key={tag.id} name={tag.name} color={tag.color} />
                  ))}
                </div>
              </td>
              {reactivationKey ? (
                <td className="px-3 py-2 text-text-secondary">
                  {reactivationValue(contact, reactivationKey)}
                </td>
              ) : null}
              <td className="px-3 py-2 text-text-secondary">
                {new Date(contact.updated_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
