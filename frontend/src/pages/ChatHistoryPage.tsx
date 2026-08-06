import { ChatHistory } from "@/features/chat-history";

/** Route page for the dedicated Chat History workspace. Full-height, so its panes scroll themselves. */
export function ChatHistoryPage(): JSX.Element {
  return (
    <div className="h-full min-h-0">
      <ChatHistory />
    </div>
  );
}
