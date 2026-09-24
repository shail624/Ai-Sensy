import { ManagePageHeader } from "@/components/layout";
import { LiveChatSettings } from "@/features/settings";

/** Manage → Live Chat Settings, laid out as the reference page. */
export function LiveChatSettingsPage(): JSX.Element {
  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Live Chat Settings" />
      <div className="px-4 py-6 sm:px-[45px]">
        <LiveChatSettings />
      </div>
    </div>
  );
}
