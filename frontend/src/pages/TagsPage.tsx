import { ManagePageHeader } from "@/components/layout";
import { TagsPanel } from "@/features/settings/TagsPanel";

/** Manage → Tags, laid out as the reference page. */
export function TagsPage(): JSX.Element {
  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Tags" />
      <div className="mx-auto max-w-[1000px] px-4 py-6 sm:px-[45px]">
        <TagsPanel />
      </div>
    </div>
  );
}
