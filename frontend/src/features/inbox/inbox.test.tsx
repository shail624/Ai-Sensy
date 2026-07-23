import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { toListQuery } from "@/features/inbox/api";
import { collateReactions } from "@/features/inbox/messageContent";
import { ConversationList } from "@/features/inbox/ConversationList";
import { MessageBubble } from "@/features/inbox/MessageBubble";
import { MessageComposer } from "@/features/inbox/MessageComposer";
import type { Conversation, Message } from "@/features/inbox/types";

// The composer and controls read permissions from the session; stub a fully entitled agent.
const permissions = { value: ["inbox:read", "inbox:write", "inbox:assign", "messages:send"] };
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions: permissions.value, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.value.includes(code),
  }),
  useHasPermission: (code: string) => permissions.value.includes(code),
}));

function conversationFixture(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: "conv1",
    type: "conversation",
    status: "open",
    channel_type: "whatsapp",
    assigned_to: null,
    contact: { id: "c1", name: "Ramesh K.", phone: "+919990000001" },
    tags: [],
    phone_number_id: "pn1",
    last_message_at: new Date().toISOString(),
    last_message_preview: "Thanks!",
    unread_count: 2,
    window: { is_open: true, expires_at: null, last_inbound_at: null },
    row_version: 0,
    created_at: "2026-07-22T10:00:00Z",
    updated_at: "2026-07-22T10:00:00Z",
    ...overrides,
  };
}

function messageFixture(overrides: Partial<Message> = {}): Message {
  return {
    id: "m1",
    type: "message",
    conversation_id: "conv1",
    direction: "outbound",
    message_type: "text",
    status: "sent",
    wamid: "wamid.1",
    content: { text: { body: "Hello there" } },
    error_code: null,
    sent_at: "2026-07-22T10:01:00Z",
    delivered_at: null,
    read_at: null,
    created_at: "2026-07-22T10:01:00Z",
    ...overrides,
  };
}

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("toListQuery", () => {
  it("nulls out unset filters so the contract sees no value", () => {
    expect(toListQuery({}, null, 25)).toEqual({
      status: null,
      assignee: null,
      tag: null,
      q: null,
      cursor: null,
      limit: 25,
    });
  });

  it("carries every filter, the cursor and the limit", () => {
    expect(toListQuery({ status: "open", assignee: "u1", tag: "t1", q: "ramesh" }, "cur1", 50)).toEqual(
      {
        status: "open",
        assignee: "u1",
        // The contract declares `tag` repeatable; the UI filters by one at a time.
        tag: ["t1"],
        q: "ramesh",
        cursor: "cur1",
        limit: 50,
      },
    );
  });
});

describe("ConversationList", () => {
  it("shows the customer, preview, status, unread count and window state", () => {
    withProviders(
      <ConversationList conversations={[conversationFixture()]} selectedId={null} onSelect={vi.fn()} />,
    );

    expect(screen.getByText("Ramesh K.")).toBeInTheDocument();
    expect(screen.getByText("Thanks!")).toBeInTheDocument();
    expect(screen.getByText("Open")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Window open")).toBeInTheDocument();
  });

  it("marks the selected conversation and reports selection", () => {
    const onSelect = vi.fn();
    withProviders(
      <ConversationList
        conversations={[conversationFixture()]}
        selectedId="conv1"
        onSelect={onSelect}
      />,
    );

    const row = screen.getByRole("button", { name: /Ramesh K./ });
    expect(row).toHaveAttribute("aria-current", "true");
    fireEvent.click(row);
    expect(onSelect).toHaveBeenCalledWith("conv1");
  });

  it("falls back to the phone number when the contact has no name", () => {
    withProviders(
      <ConversationList
        conversations={[conversationFixture({ contact: { id: "c1", name: null, phone: "+91999" } })]}
        selectedId={null}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText("+91999")).toBeInTheDocument();
  });
});

describe("MessageBubble", () => {
  it("renders the text body and an outbound receipt", () => {
    withProviders(<MessageBubble message={messageFixture()} onReact={vi.fn()} canReact />);
    expect(screen.getByText("Hello there")).toBeInTheDocument();
    expect(screen.getByText("Sent")).toBeInTheDocument();
  });

  it("escalates the receipt to Read once the customer has read it", () => {
    withProviders(
      <MessageBubble
        message={messageFixture({ delivered_at: "x", read_at: "y" })}
        onReact={vi.fn()}
        canReact
      />,
    );
    expect(screen.getByText("Read")).toBeInTheDocument();
  });

  it("surfaces a failure code", () => {
    withProviders(
      <MessageBubble
        message={messageFixture({ status: "failed", error_code: "131047" })}
        onReact={vi.fn()}
        canReact
      />,
    );
    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText("131047")).toBeInTheDocument();
  });

  it("sends the chosen reaction emoji", () => {
    const onReact = vi.fn();
    withProviders(<MessageBubble message={messageFixture()} onReact={onReact} canReact />);

    fireEvent.click(screen.getByLabelText("React to message m1"));
    fireEvent.click(screen.getByLabelText("React 👍"));

    expect(onReact).toHaveBeenCalledWith("👍");
  });

  it("hides the reaction control without messages:send", () => {
    withProviders(<MessageBubble message={messageFixture()} onReact={vi.fn()} canReact={false} />);
    expect(screen.queryByLabelText("React to message m1")).not.toBeInTheDocument();
  });
});

describe("MessageComposer", () => {
  it("blocks composing when the service window is closed", () => {
    withProviders(
      <MessageComposer
        conversation={conversationFixture({
          window: { is_open: false, expires_at: null, last_inbound_at: null },
        })}
      />,
    );

    expect(screen.getByText(/24-hour service window is closed/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Message")).toBeDisabled();
  });

  it("offers a quick-reply toggle inside an open window", () => {
    withProviders(<MessageComposer conversation={conversationFixture()} />);

    const toggle = screen.getByRole("button", { name: "Quick replies" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });

  it("keeps Send disabled until there is something to send", () => {
    withProviders(<MessageComposer conversation={conversationFixture()} />);
    expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();
  });

  it("explains itself when the user cannot send", () => {
    const original = permissions.value;
    permissions.value = ["inbox:read"];
    withProviders(<MessageComposer conversation={conversationFixture()} />);

    expect(screen.getByText(/do not have permission to send messages/i)).toBeInTheDocument();
    expect(screen.queryByLabelText("Message")).not.toBeInTheDocument();
    permissions.value = original;
  });
});

describe("message content rendering", () => {
  it("renders a media message with filename, type and caption", () => {
    withProviders(
      <MessageBubble
        message={messageFixture({
          message_type: "image",
          content: {
            media: { kind: "image", filename: "aadhaar.jpg", mime_type: "image/jpeg", caption: "Front side" },
          },
        })}
        onReact={vi.fn()}
        canReact
      />,
    );

    expect(screen.getByText("aadhaar.jpg")).toBeInTheDocument();
    expect(screen.getByText("image/jpeg")).toBeInTheDocument();
    expect(screen.getByText("Front side")).toBeInTheDocument();
  });

  it("renders a template message by name and language", () => {
    withProviders(
      <MessageBubble
        message={messageFixture({
          message_type: "template",
          content: { template: { name: "renewal_reminder", language: { code: "en_US" } } },
        })}
        onReact={vi.fn()}
        canReact
      />,
    );

    expect(screen.getByText("Template: renewal_reminder")).toBeInTheDocument();
    expect(screen.getByText("en_US")).toBeInTheDocument();
  });

  it("reads the inbound text shape as well as the outbound one", () => {
    withProviders(
      <MessageBubble
        message={messageFixture({ direction: "inbound", content: { body: "From the customer" } })}
        onReact={vi.fn()}
        canReact
      />,
    );
    expect(screen.getByText("From the customer")).toBeInTheDocument();
  });

  it("names an unmapped message type instead of rendering an empty bubble", () => {
    withProviders(
      <MessageBubble
        message={messageFixture({ message_type: "contacts", content: { contacts: [] } })}
        onReact={vi.fn()}
        canReact
      />,
    );
    expect(screen.getByText("[contacts]")).toBeInTheDocument();
  });

  it("renders reactions attached to a message", () => {
    withProviders(
      <MessageBubble
        message={messageFixture()}
        onReact={vi.fn()}
        canReact
        reactions={[{ targetWamid: "wamid.1", emoji: "👍" }]}
      />,
    );

    const list = screen.getByRole("list", { name: "Reactions" });
    expect(within(list).getByText("👍")).toBeInTheDocument();
  });
});

describe("collateReactions", () => {
  const target = messageFixture({ id: "m1", wamid: "wamid.1" });

  it("lifts a reaction onto its target and drops it from the thread", () => {
    const reaction = messageFixture({
      id: "m2",
      wamid: "wamid.2",
      message_type: "reaction",
      content: { reaction: { message_id: "wamid.1", emoji: "❤️" } },
    });

    const { thread, reactions } = collateReactions([target, reaction]);

    expect(thread.map((m) => m.id)).toEqual(["m1"]);
    expect(reactions.get("m1")).toEqual([{ targetWamid: "wamid.1", emoji: "❤️" }]);
  });

  it("treats an empty emoji as a removal", () => {
    const cleared = messageFixture({
      id: "m2",
      message_type: "reaction",
      content: { reaction: { message_id: "wamid.1", emoji: "" } },
    });

    const { thread, reactions } = collateReactions([target, cleared]);

    expect(thread.map((m) => m.id)).toEqual(["m1"]);
    expect(reactions.has("m1")).toBe(false);
  });

  it("ignores a reaction whose target is outside the loaded window", () => {
    const orphan = messageFixture({
      id: "m2",
      message_type: "reaction",
      content: { reaction: { message_id: "wamid.unknown", emoji: "👍" } },
    });

    const { thread, reactions } = collateReactions([target, orphan]);

    expect(thread.map((m) => m.id)).toEqual(["m1"]);
    expect(reactions.size).toBe(0);
  });
});
