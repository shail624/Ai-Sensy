import { useState } from "react";

import { Modal } from "@/components/ui";

/** Shared pieces of the reference Manage pages (Opt-in Management, Live Chat Settings). */

export const MANAGE_PRIMARY =
  "inline-flex h-[37px] items-center justify-center rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white transition-colors duration-200 hover:bg-[#08393d] disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";
export const MANAGE_OUTLINE =
  "inline-flex h-[30px] items-center justify-center gap-2 rounded-md border border-[rgba(10,71,76,0.5)] px-[9px] text-[13px] font-medium text-[var(--color-nav-bg)] transition-colors duration-200 hover:border-[var(--color-nav-bg)] hover:bg-[#ebf5f3] disabled:opacity-50 dark:text-accent";
export const MANAGE_CARD = "rounded-[8px] bg-surface";
export const MANAGE_FIELD =
  "rounded-[8px] bg-[#f0f0f0] px-[15px] text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-60 dark:bg-surface-2 dark:text-text-primary";

/** The reference switch: a 34x14 track with a 20px thumb; `small` is the 26x10 / 16px variant. */
export function Toggle({ checked, onChange, label, disabled, small = false }: { checked: boolean; onChange: (value: boolean) => void; label: string; disabled?: boolean; small?: boolean }): JSX.Element {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex shrink-0 items-center rounded-full transition-colors duration-150 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${small ? "h-[10px] w-[26px]" : "h-[14px] w-[34px]"} ${checked ? "bg-[rgba(10,71,76,0.5)]" : "bg-black/25"}`}
    >
      <span
        className={`absolute rounded-full shadow-[0_2px_1px_-1px_rgba(0,0,0,0.2),0_1px_1px_rgba(0,0,0,0.14),0_1px_3px_rgba(0,0,0,0.12)] transition-[left,background-color] duration-150 ${small ? "h-4 w-4" : "h-5 w-5"} ${
          checked ? `${small ? "left-[13px]" : "left-[17px]"} bg-[var(--color-nav-bg)]` : "-left-[3px] bg-[#fafafa]"
        }`}
      />
    </button>
  );
}

/** A WhatsApp-style bubble over the chat wallpaper, or a quiet placeholder when nothing is set. */
export function ResponsePreview({ body }: { body: string }): JSX.Element {
  return (
    <div className="chat-wallpaper flex min-h-[120px] items-start justify-center rounded-[8px] p-4">
      {body.trim() ? (
        <div className="w-[250px] whitespace-pre-wrap break-words rounded-[0_5px_5px_5px] bg-surface px-4 py-2 text-sm leading-[19px] text-[var(--color-nav-bg)] shadow-[0_1px_0.5px_rgba(0,0,0,0.13)] dark:text-text-primary">
          {body}
        </div>
      ) : (
        <p className="self-center text-xs text-[#808080]">No response configured</p>
      )}
    </div>
  );
}

interface ConfigureDialogProps {
  description: string;
  switchLabel: string;
  enabled: boolean;
  body: string;
  onSave: (enabled: boolean, body: string) => void;
  onClose: () => void;
}

/** The reference "Configure Message" dialog, for a regular text reply (the only kind these rules send). */
export function ConfigureDialog({ description, switchLabel, enabled, body, onSave, onClose }: ConfigureDialogProps): JSX.Element {
  const [on, setOn] = useState(enabled);
  const [text, setText] = useState(body);
  return (
    <Modal title="Configure Message" onClose={onClose} panelClassName="!max-w-[959px] !rounded-md" contentClassName="!px-6">
      <p className="text-sm text-[#6e6e6e] dark:text-text-secondary">{description}</p>
      <div className="mt-5 grid gap-6 md:grid-cols-[1fr_260px]">
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 rounded-[8px] bg-[#f5f5f5] px-4 py-3 text-sm text-[#4a4a4a] dark:bg-surface-2 dark:text-text-primary">
            Send this message
            <Toggle checked={on} onChange={setOn} label={switchLabel} />
          </div>
          <div>
            <label htmlFor="configure-message-body" className="text-sm font-medium text-text-primary">Message</label>
            <p className="text-xs text-[#6e6e6e] dark:text-text-secondary">Your message can be up to 1,000 characters long.</p>
            <textarea
              id="configure-message-body"
              value={text}
              maxLength={1000}
              rows={6}
              disabled={!on}
              onChange={(event) => setText(event.target.value)}
              placeholder="Enter the message"
              className={`${MANAGE_FIELD} mt-2 w-full resize-y py-3`}
            />
            <p className="text-right text-xs text-text-disabled">{text.length}/1,000</p>
          </div>
        </div>
        <ResponsePreview body={on ? text : ""} />
      </div>
      <div className="mt-4 flex justify-end gap-2 border-t border-border pt-3">
        <button type="button" onClick={onClose} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover dark:text-text-secondary">Cancel</button>
        <button type="button" onClick={() => { onSave(on, text); onClose(); }} className={MANAGE_PRIMARY}>Save Configuration</button>
      </div>
    </Modal>
  );
}
