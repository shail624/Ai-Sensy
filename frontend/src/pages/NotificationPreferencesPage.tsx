import { Bell, Monitor, Volume2 } from "lucide-react";
import { useState } from "react";

import { ManagePageHeader } from "@/components/layout";
import { playChime, useAlertPrefs } from "@/features/inbox/messageAlerts";
import { NotificationSettingsPanel } from "@/features/notifications/NotificationSettingsPanel";
import { Toggle } from "@/features/settings/managePrimitives";
import { QuickGuide } from "@/features/settings/QuickGuide";

type Permission = NotificationPermission | "unsupported";

function currentPermission(): Permission {
  return typeof Notification === "undefined" ? "unsupported" : Notification.permission;
}

/**
 * Manage → Notification Preferences, laid out as the reference: sound, desktop (push) alerts for
 * this device, then which kinds of updates reach your notification bell.
 */
export function NotificationPreferencesPage(): JSX.Element {
  const [prefs, setPrefs] = useAlertPrefs();
  const [permission, setPermission] = useState<Permission>(currentPermission);

  async function setDesktop(on: boolean): Promise<void> {
    if (!on) {
      setPrefs({ ...prefs, desktop: false });
      return;
    }
    if (permission === "unsupported") return;
    const result = permission === "granted" ? "granted" : await Notification.requestPermission();
    setPermission(result);
    setPrefs({ ...prefs, desktop: result === "granted" });
  }

  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Notification Preferences" />
      <div className="mx-auto max-w-[1000px] space-y-5 px-4 py-6 sm:px-[45px]">
        <QuickGuide
          eyebrow="Notification quick guide"
          text="Choose how you hear about new customer messages and reminders. Sound and desktop alerts are set for this browser; the list below is saved to your account."
        />

        <section className="rounded-[8px] bg-surface">
          <div className="flex items-center gap-4 border-b border-[#f0f0f0] px-5 py-4 dark:border-border">
            <Volume2 aria-hidden className="h-5 w-5 text-[var(--color-nav-bg)] dark:text-accent" />
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold text-black dark:text-text-primary">Sound Notification</h2>
              <p className="text-xs text-[#6e6e6e] dark:text-text-secondary">Play a short sound when a customer messages or a reminder is due.</p>
            </div>
            <button type="button" onClick={playChime} className="text-xs font-medium text-[var(--color-nav-bg)] hover:underline dark:text-accent">
              Test sound
            </button>
            <Toggle checked={prefs.sound} onChange={(sound) => setPrefs({ ...prefs, sound })} label="Sound notification" />
          </div>

          <div className="flex items-center gap-4 px-5 py-4">
            <Monitor aria-hidden className="h-5 w-5 text-[var(--color-nav-bg)] dark:text-accent" />
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold text-black dark:text-text-primary">Push Notification (this device)</h2>
              <p className="text-xs text-[#6e6e6e] dark:text-text-secondary">
                {permission === "unsupported"
                  ? "This browser cannot show desktop notifications."
                  : permission === "denied"
                    ? "Blocked in this browser. Click the lock icon next to the address, allow Notifications, then reload."
                    : "Show a pop-up on this computer, even when the app is in the background."}
              </p>
            </div>
            <Toggle
              checked={prefs.desktop && permission === "granted"}
              disabled={permission === "unsupported" || permission === "denied"}
              onChange={(on) => void setDesktop(on)}
              label="Push notification on this device"
            />
          </div>
        </section>

        <section className="overflow-hidden rounded-[8px] bg-surface">
          <div className="flex items-center gap-3 border-b border-[#f0f0f0] px-5 py-4 dark:border-border">
            <Bell aria-hidden className="h-5 w-5 text-[var(--color-nav-bg)] dark:text-accent" />
            <div>
              <h2 className="text-sm font-semibold text-black dark:text-text-primary">Bell notifications</h2>
              <p className="text-xs text-[#6e6e6e] dark:text-text-secondary">Which updates appear in your notification bell. Saved as soon as you change them.</p>
            </div>
          </div>
          <NotificationSettingsPanel open />
        </section>
      </div>
    </div>
  );
}
