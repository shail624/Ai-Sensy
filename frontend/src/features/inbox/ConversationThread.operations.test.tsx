import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ConversationThread } from "@/features/inbox/ConversationThread";

const state = vi.hoisted(() => ({
  autoMarkRead: true,
  markRead: vi.fn(),
}));

vi.mock("@/features/settings/api", () => ({
  useInboxOperations: () => ({
    data: { auto_mark_read: state.autoMarkRead },
    isSuccess: true,
  }),
}));

vi.mock("@/features/inbox/api", () => ({
  useUpdateSaleDetails: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  apiErrorMessage: () => "error",
  useConversation: () => ({
    data: {
      id: "conv-1",
      contact: { name: "Priya", phone: "+919999999999" },
      unread_count: 3,
      connector_type: "meta_cloud",
      channel_type: "whatsapp",
      window: { is_open: true },
    },
    isLoading: false,
    isError: false,
  }),
  useMessages: () => ({ data: { pages: [{ data: [] }] }, isLoading: false, isError: false }),
  useMarkRead: () => ({ mutate: state.markRead, isPending: false }),
  useSendReaction: () => ({ mutate: vi.fn(), error: null }),
}));

vi.mock("@/features/inbox/ConversationControls", () => ({
  AssignmentControl: () => <div>Assignment</div>,
  StatusControl: () => <div>Status</div>,
}));
vi.mock("@/features/inbox/InterventionActions", () => ({ InterventionActions: () => null }));
vi.mock("@/features/inbox/MessageComposer", () => ({ MessageComposer: () => <div>Composer</div> }));
vi.mock("@/features/inbox/InboxContextPanel", () => ({ InboxContextPanel: () => null }));
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ user: { id: "agent-1" } }),
  useHasPermission: () => true,
}));

describe("ConversationThread operational read policy", () => {
  beforeEach(() => {
    state.autoMarkRead = true;
    state.markRead.mockReset();
  });

  it("clears unread state when the organization enables automatic read clearing", async () => {
    render(<ConversationThread conversationId="conv-1" tags={[]} />);
    await waitFor(() => expect(state.markRead).toHaveBeenCalledWith(undefined));
  });

  it("offers a deliberate mark-read action when automatic clearing is disabled", async () => {
    state.autoMarkRead = false;
    const view = render(<ConversationThread conversationId="conv-1" tags={[]} />);
    expect(state.markRead).not.toHaveBeenCalled();
    view.getByRole("button", { name: "Mark read" }).click();
    await waitFor(() => expect(state.markRead).toHaveBeenCalledWith(undefined));
  });
});
