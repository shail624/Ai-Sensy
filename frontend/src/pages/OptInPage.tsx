import { ManagePageHeader } from "@/components/layout";
import { OptInManagement } from "@/features/settings";

/** Manage → Opt-in Management, laid out as the reference page. */
export function OptInPage(): JSX.Element {
  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Opt-in Management" />
      <div className="px-4 py-6 sm:px-[45px]">
        <OptInManagement />
      </div>
    </div>
  );
}
