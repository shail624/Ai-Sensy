import { AlarmClock, CalendarDays, StickyNote, X } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useUpdateSaleDetails } from "@/features/inbox/api";
import { NotesPanel } from "@/features/inbox/NotesPanel";
import { formatDay, isSaleStatus, SALE_STATUS_OPTIONS, saleStatusOption } from "@/features/inbox/saleStatus";
import type { Conversation } from "@/features/inbox/types";
import { useCreateTask } from "@/features/tasks/api";
import { useHasPermission } from "@/lib/auth";

const chip =
  "inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border border-[rgba(10,71,76,0.35)] px-3 text-xs font-medium text-[var(--color-nav-bg)] transition hover:bg-[#ebf5f3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-50 dark:text-accent";

/** Sale status, number release date, reminder and notes — one row above the chat. */
export function SaleControls({ conversation }: { conversation: Conversation }): JSX.Element | null {
  const canWrite = useHasPermission("inbox:write");
  const update = useUpdateSaleDetails(conversation.id);
  const [dialog, setDialog] = useState<"release" | "reminder" | "notes" | null>(null);
  const contact = conversation.contact;
  if (!contact) return null;
  // Show the chosen status straight away; the chat refreshes a moment later with the saved value.
  const pending = update.isPending && update.variables && "sale_status" in update.variables;
  const current = saleStatusOption(pending ? update.variables?.sale_status : contact.sale_status);
  const releaseDate = contact.release_date ?? null;

  return (
    <div className="flex shrink-0 items-center gap-2 overflow-x-auto border-b border-[#f2f2f2] bg-[#fdfffc] px-3 py-2 dark:border-border dark:bg-surface">
      <label className="sr-only" htmlFor={`sale-status-${conversation.id}`}>Sale status</label>
      <select
        id={`sale-status-${conversation.id}`}
        disabled={!canWrite || update.isPending}
        value={current?.value ?? ""}
        onChange={(event) => {
          const value = event.target.value;
          update.mutate({ sale_status: isSaleStatus(value) ? value : null });
        }}
        className={`h-9 shrink-0 cursor-pointer rounded-full border-0 pl-3 pr-8 text-xs font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${current ? current.pill : "bg-[#f0f0f0] text-[#4a4a4a] dark:bg-surface-2 dark:text-text-secondary"}`}
      >
        <option value="">Mark sale status…</option>
        {SALE_STATUS_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>

      <button type="button" disabled={!canWrite} onClick={() => setDialog("release")} className={chip}>
        <CalendarDays aria-hidden className="h-4 w-4" />
        {releaseDate ? `Release: ${formatDay(releaseDate)}` : "Release date"}
      </button>
      <button type="button" disabled={!canWrite} onClick={() => setDialog("reminder")} className={chip}>
        <AlarmClock aria-hidden className="h-4 w-4" /> Reminder
      </button>
      <button type="button" onClick={() => setDialog("notes")} className={chip}>
        <StickyNote aria-hidden className="h-4 w-4" /> Notes
      </button>
      {update.error ? <span role="alert" className="text-xs text-danger">{apiErrorMessage(update.error)}</span> : null}

      {dialog === "release" ? (
        <ReleaseDateDialog conversation={conversation} initial={releaseDate} onClose={() => setDialog(null)} />
      ) : null}
      {dialog === "reminder" ? <ReminderDialog conversation={conversation} onClose={() => setDialog(null)} /> : null}
      {dialog === "notes" ? (
        <Modal title="Notes" onClose={() => setDialog(null)} panelClassName="!max-w-[480px] !rounded-md" contentClassName="!px-6">
          <NotesPanel conversationId={conversation.id} />
        </Modal>
      ) : null}
    </div>
  );
}

const input =
  "mt-2 h-[42px] w-full rounded-[8px] bg-[#f0f0f0] px-[15px] text-sm text-[#4a4a4a] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:bg-surface-2 dark:text-text-primary";
const primary =
  "inline-flex h-9 items-center rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white transition-colors hover:bg-[#08393d] disabled:opacity-60";
const secondary = "h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover dark:text-text-secondary";

function ReleaseDateDialog({ conversation, initial, onClose }: { conversation: Conversation; initial: string | null; onClose: () => void }): JSX.Element {
  const [day, setDay] = useState(initial ?? "");
  const update = useUpdateSaleDetails(conversation.id);

  function save(value: string | null): void {
    update.mutate({ release_date: value }, { onSuccess: onClose });
  }

  return (
    <Modal title="Number release date" onClose={onClose} panelClassName="!max-w-[420px] !rounded-md" contentClassName="!px-6">
      <form onSubmit={(event: FormEvent) => { event.preventDefault(); if (day) save(day); }} className="space-y-4">
        <div>
          <label htmlFor="release-date" className="text-sm font-medium text-text-primary">Release date</label>
          <input id="release-date" type="date" value={day} onChange={(event) => setDay(event.target.value)} className={input} />
          <p className="mt-1.5 text-xs text-[#6e6e6e] dark:text-text-secondary">
            You will get a reminder at 10:00 AM on this date (bell icon). It also appears in Tasks.
          </p>
        </div>
        {update.error ? <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-on-soft">{apiErrorMessage(update.error)}</p> : null}
        <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
          {initial ? (
            <button type="button" onClick={() => save(null)} className={`${secondary} mr-auto inline-flex items-center gap-1 text-danger`}>
              <X aria-hidden className="h-4 w-4" /> Remove date
            </button>
          ) : null}
          <button type="button" onClick={onClose} className={secondary}>Cancel</button>
          <button type="submit" disabled={!day || update.isPending} className={primary}>{update.isPending ? "Saving…" : "Save"}</button>
        </div>
      </form>
    </Modal>
  );
}

function todayLocal(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

function ReminderDialog({ conversation, onClose }: { conversation: Conversation; onClose: () => void }): JSX.Element {
  const [day, setDay] = useState(todayLocal());
  const [time, setTime] = useState("10:00");
  const [note, setNote] = useState("");
  const create = useCreateTask();
  const name = conversation.contact?.name ?? conversation.contact?.phone ?? "customer";

  function submit(event: FormEvent): void {
    event.preventDefault();
    if (!day || !conversation.contact) return;
    const due = new Date(`${day}T${time || "10:00"}`).toISOString();
    create.mutate(
      {
        contact_id: conversation.contact.id,
        conversation_id: conversation.id,
        title: note.trim() ? note.trim().slice(0, 120) : `Contact ${name}`,
        task_type: "reminder",
        priority: "medium",
        due_at: due,
        has_time: true,
        reminder_at: due,
        description: note.trim() || null,
      },
      { onSuccess: onClose },
    );
  }

  return (
    <Modal title={`Reminder for ${name}`} onClose={onClose} panelClassName="!max-w-[420px] !rounded-md" contentClassName="!px-6">
      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label htmlFor="reminder-day" className="text-sm font-medium text-text-primary">Date</label>
            <input id="reminder-day" type="date" required value={day} onChange={(event) => setDay(event.target.value)} className={input} />
          </div>
          <div>
            <label htmlFor="reminder-time" className="text-sm font-medium text-text-primary">Time</label>
            <input id="reminder-time" type="time" value={time} onChange={(event) => setTime(event.target.value)} className={input} />
          </div>
        </div>
        <div>
          <label htmlFor="reminder-note" className="text-sm font-medium text-text-primary">What to do</label>
          <textarea id="reminder-note" rows={3} value={note} onChange={(event) => setNote(event.target.value)} placeholder="e.g. Call back about the new plan" className={`${input} h-auto py-2`} />
        </div>
        <p className="text-xs text-[#6e6e6e] dark:text-text-secondary">You will be reminded at this time in the bell icon. Open reminders are listed in Tasks.</p>
        {create.error ? <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-on-soft">{apiErrorMessage(create.error)}</p> : null}
        <div className="flex justify-end gap-2 border-t border-border pt-3">
          <button type="button" onClick={onClose} className={secondary}>Cancel</button>
          <button type="submit" disabled={!day || create.isPending} className={primary}>{create.isPending ? "Saving…" : "Set reminder"}</button>
        </div>
      </form>
    </Modal>
  );
}
