import { ManagePageHeader } from "@/components/layout";
import { UserAttributesPanel } from "@/features/settings";

/** Manage → User Attributes, laid out as the reference page. */
export function UserAttributesPage(): JSX.Element {
  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="User Attributes" />
      <div className="px-4 py-6 sm:px-[45px]">
        <UserAttributesPanel />
      </div>
    </div>
  );
}
