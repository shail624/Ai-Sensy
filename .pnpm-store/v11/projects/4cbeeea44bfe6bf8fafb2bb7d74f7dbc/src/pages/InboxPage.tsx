import { Inbox } from "@/features/inbox";

/** Route page for the Shared Inbox (Doc 02 Phase 7). Full-height, so the thread scrolls itself. */
export function InboxPage(): JSX.Element {
  return (
    <div className="h-full min-h-0">
      <Inbox />
    </div>
  );
}
