import { useState, type FormEvent } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useStartChat } from "@/features/inbox/api";

interface Props {
  onClose: () => void;
  /** Called with the conversation to open once WhatsApp confirms the number. */
  onStarted: (conversationId: string) => void;
}

/**
 * Start a chat with someone who has not messaged yet, over the QR-connected WhatsApp. WhatsApp is
 * asked first whether the number has an account, so a typo never creates an empty chat.
 */
export function NewChatDialog({ onClose, onStarted }: Props): JSX.Element {
  const [phone, setPhone] = useState("");
  const start = useStartChat();

  function submit(event: FormEvent): void {
    event.preventDefault();
    if (!phone.trim()) return;
    start.mutate(phone, {
      onSuccess: (conversationId) => {
        onStarted(conversationId);
        onClose();
      },
    });
  }

  return (
    <Modal title="New chat" onClose={onClose} panelClassName="!max-w-[440px] !rounded-md" contentClassName="!px-6">
      <form onSubmit={submit} className="space-y-4" noValidate>
        <div>
          <label htmlFor="new-chat-phone" className="text-sm font-medium text-text-primary">Mobile number</label>
          <input
            id="new-chat-phone"
            type="tel"
            inputMode="tel"
            autoComplete="off"
            autoFocus
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            placeholder="98765 43210"
            className="mt-2 h-[42px] w-full rounded-[8px] bg-[#f0f0f0] px-[15px] text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:bg-surface-2 dark:text-text-primary"
          />
          <p className="mt-1.5 text-xs text-[#6e6e6e] dark:text-text-secondary">
            A 10-digit number is treated as Indian (+91). For other countries, include the country code.
          </p>
        </div>
        {start.error ? (
          <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-on-soft">{apiErrorMessage(start.error)}</p>
        ) : null}
        <div className="flex justify-end gap-2 border-t border-border pt-3">
          <button type="button" onClick={onClose} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover dark:text-text-secondary">Cancel</button>
          <button
            type="submit"
            disabled={!phone.trim() || start.isPending}
            className="inline-flex h-9 items-center rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white transition-colors hover:bg-[#08393d] disabled:opacity-60"
          >
            {start.isPending ? "Checking WhatsApp…" : "Start chat"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
