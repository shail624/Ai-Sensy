import { ManagePageHeader } from "@/components/layout";
import { CannedMessagesPanel } from "@/features/settings/CannedMessagesPanel";

/** Manage → Canned Messages, laid out as the reference page. */
export function CannedMessagesPage(): JSX.Element {
  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Canned Messages" />
      <div className="mx-auto max-w-[1000px] px-4 py-6 sm:px-[45px]">
        <CannedMessagesPanel />
      </div>
    </div>
  );
}
