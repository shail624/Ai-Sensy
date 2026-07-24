import { ChevronRight } from "lucide-react";
import { useEffect, useRef, type PointerEvent as ReactPointerEvent } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Avatar, Badge, TagChip } from "@/components/ui";
import type { BadgeTone } from "@/components/ui";
import type { Contact } from "@/features/contacts/types";
import { useIsCompact } from "@/lib/useMediaQuery";

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
const CHECKBOX = "h-4 w-4 accent-[var(--color-accent)]";
/** Slightly larger on the phone cards, where the control is a touch target rather than a click target. */
const TOUCH_CHECKBOX = "h-5 w-5 accent-[var(--color-accent)]";

/** Press-and-hold duration that starts a selection on touch (Doc 05 B3.1 "bulk via long-press"). */
const LONG_PRESS_MS = 500;
/** Movement beyond this cancels the press — it was a scroll, not a hold. */
const LONG_PRESS_SLOP_PX = 10;

/**
 * The contacts list. At `md` and above this is the standard table (DS-14); below it the same rows
 * reflow to stacked cards (DS-14 "Responsive", B3.1 "Mobile"). Exactly one of the two is mounted,
 * so the row content is never duplicated in the DOM or announced twice.
 */
export function ContactsTable({
  contacts,
  selectedIds,
  onToggle,
  onToggleAll,
  reactivationKey,
}: Props): JSX.Element {
  const compact = useIsCompact();
  const allSelected = contacts.length > 0 && contacts.every((contact) => selectedIds.has(contact.id));

  if (compact) {
    return (
      <ContactCards
        contacts={contacts}
        selectedIds={selectedIds}
        onToggle={onToggle}
        onToggleAll={onToggleAll}
        allSelected={allSelected}
        reactivationKey={reactivationKey}
      />
    );
  }

  return (
    <ContactRows
      contacts={contacts}
      selectedIds={selectedIds}
      onToggle={onToggle}
      onToggleAll={onToggleAll}
      allSelected={allSelected}
      reactivationKey={reactivationKey}
    />
  );
}

interface ViewProps extends Props {
  allSelected: boolean;
}

/** Desktop / tablet — the standard table. */
function ContactRows({
  contacts,
  selectedIds,
  onToggle,
  onToggleAll,
  allSelected,
  reactivationKey,
}: ViewProps): JSX.Element {
  const navigate = useNavigate();

  return (
    <div className="overflow-x-auto rounded-2xl border border-border bg-surface shadow-sm">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-border bg-surface-2">
            <th scope="col" className="w-11 px-4 py-2.5">
              <input
                type="checkbox"
                aria-label="Select all contacts on this page"
                checked={allSelected}
                onChange={onToggleAll}
                className={CHECKBOX}
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
                  selected ? "bg-accent-soft" : ""
                }`}
              >
                <td className={`${TD} py-3`} onClick={(event) => event.stopPropagation()}>
                  <input
                    type="checkbox"
                    aria-label={`Select ${displayName(contact)}`}
                    checked={selected}
                    onChange={() => onToggle(contact.id)}
                    className={CHECKBOX}
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

/** Phone — stacked cards carrying the same fields the table columns carry. */
function ContactCards({
  contacts,
  selectedIds,
  onToggle,
  onToggleAll,
  allSelected,
  reactivationKey,
}: ViewProps): JSX.Element {
  const selectionActive = selectedIds.size > 0;

  return (
    <div>
      <div className="mb-2 flex items-center gap-1 px-1">
        {/* The label carries the padding, so the tap target clears 24×24 (WCAG 2.5.8). */}
        <label className="-m-1 flex cursor-pointer items-center p-2.5">
          <input
            type="checkbox"
            aria-label="Select all contacts on this page"
            checked={allSelected}
            onChange={onToggleAll}
            className={TOUCH_CHECKBOX}
          />
        </label>
        <span className="text-xs font-medium text-text-secondary">
          {selectionActive ? `${selectedIds.size} selected` : "Select all"}
        </span>
        <span className="ml-auto text-xs text-text-disabled">Hold a card to select</span>
      </div>
      <ul className="space-y-2.5">
        {contacts.map((contact) => (
          <ContactCard
            key={contact.id}
            contact={contact}
            selected={selectedIds.has(contact.id)}
            selectionActive={selectionActive}
            onToggle={onToggle}
            reactivationKey={reactivationKey}
          />
        ))}
      </ul>
    </div>
  );
}

interface CardProps {
  contact: Contact;
  selected: boolean;
  /** Once anything is selected, a plain tap toggles selection instead of opening the profile. */
  selectionActive: boolean;
  onToggle: (id: string) => void;
  reactivationKey: string | null;
}

function ContactCard({
  contact,
  selected,
  selectionActive,
  onToggle,
  reactivationKey,
}: CardProps): JSX.Element {
  const navigate = useNavigate();
  const status = statusFor(contact);
  const name = displayName(contact);

  const timer = useRef<number | null>(null);
  const origin = useRef<{ x: number; y: number } | null>(null);
  const heldRef = useRef(false);

  function cancelPress(): void {
    if (timer.current !== null) {
      window.clearTimeout(timer.current);
      timer.current = null;
    }
    origin.current = null;
  }

  useEffect(
    () => () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
    },
    [],
  );

  function onPointerDown(event: ReactPointerEvent<HTMLLIElement>): void {
    if (event.pointerType === "mouse") return; // hold-to-select is a touch/pen gesture
    heldRef.current = false;
    origin.current = { x: event.clientX, y: event.clientY };
    timer.current = window.setTimeout(() => {
      heldRef.current = true;
      timer.current = null;
      onToggle(contact.id);
    }, LONG_PRESS_MS);
  }

  function onPointerMove(event: ReactPointerEvent<HTMLLIElement>): void {
    const start = origin.current;
    if (!start) return;
    if (Math.abs(event.clientX - start.x) > LONG_PRESS_SLOP_PX || Math.abs(event.clientY - start.y) > LONG_PRESS_SLOP_PX) {
      cancelPress(); // the finger is scrolling
    }
  }

  function onClick(): void {
    cancelPress();
    if (heldRef.current) {
      heldRef.current = false; // consume the click that follows the hold
      return;
    }
    if (selectionActive) {
      onToggle(contact.id);
      return;
    }
    navigate(`/contacts/${contact.id}`);
  }

  return (
    <li
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={cancelPress}
      onPointerCancel={cancelPress}
      onClick={onClick}
      className={`select-none rounded-2xl border p-3.5 shadow-sm transition-colors ${
        selected ? "border-accent bg-accent-soft" : "border-border bg-surface"
      }`}
    >
      <div className="flex items-start gap-3">
        {/* The label carries the padding, so the tap target clears 24×24 (WCAG 2.5.8). */}
        <label className="-m-2 cursor-pointer p-2" onClick={(event) => event.stopPropagation()}>
          <input
            type="checkbox"
            aria-label={`Select ${name}`}
            checked={selected}
            onChange={() => onToggle(contact.id)}
            className={TOUCH_CHECKBOX}
          />
        </label>
        <Avatar name={name} size="sm" />
        <div className="min-w-0 flex-1">
          <Link
            to={`/contacts/${contact.id}`}
            onClick={(event) => event.stopPropagation()}
            className="block truncate font-semibold text-text-primary focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            {name}
          </Link>
          <p className="mt-0.5 truncate text-[13px] tabular-nums text-text-secondary">{contact.phone_e164}</p>
        </div>
        <ChevronRight aria-hidden className="mt-1 h-4 w-4 shrink-0 text-text-disabled" />
      </div>

      <div className="mt-2.5 flex flex-wrap items-center gap-1.5 pl-7">
        <Badge tone={status.tone} dot>
          {status.label}
        </Badge>
        {contact.tags.map((tag) => (
          <TagChip key={tag.id} name={tag.name} color={tag.color} />
        ))}
      </div>

      <dl className="mt-2.5 flex flex-wrap items-center gap-x-4 gap-y-1 pl-7 text-xs">
        {reactivationKey ? (
          <div className="flex items-center gap-1.5">
            <dt className="text-text-disabled">Reactivation status</dt>
            <dd className="font-medium text-text-secondary">{reactivationValue(contact, reactivationKey)}</dd>
          </div>
        ) : null}
        <div className="flex items-center gap-1.5">
          <dt className="text-text-disabled">Last active</dt>
          <dd className="font-medium text-text-secondary">{lastActive(contact)}</dd>
        </div>
      </dl>
    </li>
  );
}
