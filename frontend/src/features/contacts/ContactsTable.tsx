import { ChevronRight } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { Avatar, Badge, TagChip } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import type { Contact } from "@/features/contacts/types";

function displayName(contact: Contact): string {
  return contact.full_name ?? contact.profile_name ?? contact.phone_e164;
}

function reactivationValue(contact: Contact, key: string | null): string {
  if (!key) return "—";
  const value = contact.attributes[key];
  return value === undefined || value === null || value === "" ? "—" : String(value);
}

/** Opt-in status → a status pill. The API vocabulary is the source; unknown values render neutrally. */
const OPT_IN: Record<string, { tone: BadgeTone; label: string }> = {
  opted_in: { tone: "success", label: "Opted in" },
  opted_out: { tone: "danger", label: "Opted out" },
  pending: { tone: "warning", label: "Pending" },
  unknown: { tone: "neutral", label: "Unknown" },
};

function statusFor(contact: Contact): { tone: BadgeTone; label: string } {
  return OPT_IN[contact.opt_in_status] ?? { tone: "neutral", label: contact.opt_in_status };
}

/** Last activity — most recent of the contact's timestamps, shown relatively. */
function lastActive(contact: Contact): string {
  const stamp =
    contact.last_contacted_at ?? contact.last_inbound_at ?? contact.last_outbound_at ?? contact.updated_at;
  const then = Date.parse(stamp);
  if (Number.isNaN(then)) return "—";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(then).toLocaleDateString();
}

interface Props {
  contacts: Contact[];
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: () => void;
  /** Custom-attribute key to surface as a "Reactivation status" column, when one is defined. */
  reactivationKey: string | null;
}

const TH = "px-4 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wide text-text-disabled";
const TD = "px-4 py-3 align-middle";

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
    <div className="overflow-x-auto rounded-2xl border border-border bg-surface shadow-sm">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-surface-2/60">
            <th scope="col" className="w-11 px-4 py-2.5">
              <input
                type="checkbox"
                aria-label="Select all contacts on this page"
                checked={allSelected}
                onChange={onToggleAll}
                className="h-4 w-4 accent-[var(--color-accent)]"
              />
            </th>
            <th scope="col" className={TH}>Name</th>
            <th scope="col" className={TH}>Phone</th>
            <th scope="col" className={TH}>Tags</th>
            <th scope="col" className={TH}>Status</th>
            {reactivationKey ? <th scope="col" className={TH}>Reactivation status</th> : null}
            <th scope="col" className={TH}>Last active</th>
            <th scope="col" className="w-10 px-4 py-2.5" aria-label="Actions" />
          </tr>
        </thead>
        <tbody>
          {contacts.map((contact) => {
            const status = statusFor(contact);
            const selected = selectedIds.has(contact.id);
            return (
              <tr
                key={contact.id}
                onClick={() => navigate(`/contacts/${contact.id}`)}
                className={`group cursor-pointer border-b border-border transition-colors last:border-0 hover:bg-hover ${
                  selected ? "bg-accent-soft/50" : ""
                }`}
              >
                <td className={`${TD} py-3`} onClick={(event) => event.stopPropagation()}>
                  <input
                    type="checkbox"
                    aria-label={`Select ${displayName(contact)}`}
                    checked={selected}
                    onChange={() => onToggle(contact.id)}
                    className="h-4 w-4 accent-[var(--color-accent)]"
                  />
                </td>
                <td className={TD}>
                  <div className="flex items-center gap-3">
                    <Avatar name={displayName(contact)} size="sm" />
                    <Link
                      to={`/contacts/${contact.id}`}
                      onClick={(event) => event.stopPropagation()}
                      className="font-semibold text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    >
                      {displayName(contact)}
                    </Link>
                  </div>
                </td>
                <td className={`${TD} tabular-nums text-text-secondary`}>{contact.phone_e164}</td>
                <td className={TD}>
                  <div className="flex flex-wrap gap-1">
                    {contact.tags.length === 0 ? (
                      <span className="text-text-disabled">—</span>
                    ) : (
                      contact.tags.map((tag) => <TagChip key={tag.id} name={tag.name} color={tag.color} />)
                    )}
                  </div>
                </td>
                <td className={TD}>
                  <Badge tone={status.tone} dot>
                    {status.label}
                  </Badge>
                </td>
                {reactivationKey ? (
                  <td className={`${TD} text-text-secondary`}>{reactivationValue(contact, reactivationKey)}</td>
                ) : null}
                <td className={`${TD} text-text-secondary`}>{lastActive(contact)}</td>
                <td className={TD}>
                  <ChevronRight
                    aria-hidden
                    className="h-4 w-4 text-text-disabled opacity-0 transition-opacity group-hover:opacity-100"
                  />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
