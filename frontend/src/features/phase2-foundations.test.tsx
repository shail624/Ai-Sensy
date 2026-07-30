import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { navItems, visibleNavItems } from "@/components/layout/navigation";
import { AiFoundationPanel } from "@/features/ai";
import { EngagementFunnel } from "@/features/analytics";
import { InboxContextPanel } from "@/features/inbox/InboxContextPanel";
import type { Conversation } from "@/features/inbox/types";

vi.mock("@/lib/auth", () => ({
  useHasPermission: () => true,
}));

const conversation: Conversation = {
  id: "conv-1",
  type: "conversation",
  status: "open",
  channel_type: "whatsapp",
  assigned_to: "agent-1",
  contact: { id: "contact-1", name: "Asha", phone: "+919900000001" },
  tags: [{ id: "tag-1", name: "Priority", color: "#4f46e5" }],
  phone_number_id: "number-1",
  last_message_at: "2026-07-25T10:00:00Z",
  last_message_preview: "I am interested",
  unread_count: 1,
  window: { is_open: true, expires_at: null, last_inbound_at: null },
  row_version: 1,
  created_at: "2026-07-25T09:00:00Z",
  updated_at: "2026-07-25T10:00:00Z",
};

describe("Phase 2 engagement foundations", () => {
  it("exposes Broadcast Center only through the campaign permission", () => {
    const broadcast = navItems.find((item) => item.path === "/broadcasts");
    expect(broadcast?.permission).toBe("campaigns:read");
    expect(visibleNavItems((code) => code === "campaigns:read").map((item) => item.label)).toContain("Broadcasts");
  });

  it("keeps AI assistance visibly human-controlled and non-operational", () => {
    render(<AiFoundationPanel capabilities={["reply", "summary"]} context="a customer conversation" />);
    expect(screen.getByText("Nothing is generated or sent automatically")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "AI summary" }));
    expect(screen.getByRole("heading", { name: "AI summary" })).toBeInTheDocument();
    expect(screen.getByText(/governed AI service/)).toBeInTheDocument();
  });

  it("renders the delivery funnel from verified totals and never invents an empty result", () => {
    const { rerender } = render(<EngagementFunnel totals={{ messages_sent: 100, messages_delivered: 80, messages_read: 40 }} />);
    expect(screen.getByText(/80.0%/)).toBeInTheDocument();
    expect(screen.getByText(/50.0%/)).toBeInTheDocument();
    rerender(<EngagementFunnel totals={{}} />);
    expect(screen.getByText("No delivery funnel yet")).toBeInTheDocument();
  });

  it("keeps customer context beside the thread and marks merge as contract-gated", () => {
    const onTogglePinned = vi.fn();
    const onClose = vi.fn();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <InboxContextPanel conversation={conversation} tags={conversation.tags} pinned={false} onTogglePinned={onTogglePinned} onClose={onClose} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText("Asha")).toBeInTheDocument();
    expect(screen.getByText("Priority")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Merge" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Pin" }));
    expect(onTogglePinned).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("button", { name: "Close details" }));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
