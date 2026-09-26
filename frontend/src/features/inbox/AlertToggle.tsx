import { Volume2, VolumeX } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { playChime, useAlertPrefs } from "@/features/inbox/messageAlerts";

/**
 * The new-message alert switch: sound and desktop notifications, each on or off. Desktop
 * notifications ask the browser's permission the moment they are switched on (browsers only allow
 * that from a click), and say so plainly when the browser has blocked them.
 */
export function AlertToggle(): JSX.Element {
  const [prefs, setPrefs] = useAlertPrefs();
  const [open, setOpen] = useState(false);
  const [permission, setPermission] = useState<NotificationPermission | "unsupported">(
    typeof Notification === "undefined" ? "unsupported" : Notification.permission,
  );
  const ref = useRef<HTMLDivElement>(null);
  const on = prefs.sound || prefs.desktop;

  useEffect(() => {
    if (!open) return undefined;
    const close = (event: MouseEvent): void => {
      if (!ref.current?.contains(event.target as Node)) setOpen(false);
    };
    const escape = (event: KeyboardEvent): void => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  async function toggleDesktop(checked: boolean): Promise<void> {
    if (checked && permission === "default") {
      const result = await Notification.requestPermission();
      setPermission(result);
      if (result !== "granted") return;
    }
    setPrefs({ ...prefs, desktop: checked && permission !== "denied" });
  }

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        aria-label={on ? "New message alerts on" : "New message alerts off"}
        aria-expanded={open}
        title="New message alerts"
        onClick={() => setOpen((value) => !value)}
        className="flex h-[30px] w-[30px] items-center justify-center rounded-full text-text-secondary transition-colors hover:bg-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
      >
        {on ? <Volume2 aria-hidden className="h-[18px] w-[18px]" /> : <VolumeX aria-hidden className="h-[18px] w-[18px]" />}
      </button>
      {open ? (
        <div role="dialog" aria-label="New message alerts" className="absolute right-0 z-40 mt-2 w-64 rounded-lg border border-border bg-surface p-3 text-sm shadow-lg">
          <p className="mb-2 font-medium text-text-primary">When a customer messages</p>
          <label className="flex items-center justify-between gap-3 py-1.5 text-text-primary">
            Play a sound
            <input
              type="checkbox"
              checked={prefs.sound}
              onChange={(event) => {
                setPrefs({ ...prefs, sound: event.target.checked });
                if (event.target.checked) playChime();
              }}
              className="h-4 w-4 accent-[var(--color-nav-bg)]"
            />
          </label>
          <label className="flex items-center justify-between gap-3 py-1.5 text-text-primary">
            Show a desktop notification
            <input
              type="checkbox"
              checked={prefs.desktop && permission === "granted"}
              disabled={permission === "unsupported" || permission === "denied"}
              onChange={(event) => void toggleDesktop(event.target.checked)}
              className="h-4 w-4 accent-[var(--color-nav-bg)]"
            />
          </label>
          {permission === "denied" ? (
            <p className="mt-1 text-xs text-danger">Notifications are blocked in this browser. Allow them from the lock icon in the address bar.</p>
          ) : permission === "unsupported" ? (
            <p className="mt-1 text-xs text-text-secondary">This browser does not support desktop notifications.</p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
