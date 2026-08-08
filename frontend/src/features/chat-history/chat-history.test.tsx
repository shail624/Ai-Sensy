import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes, useSearchParams } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { navItems } from "@/components/layout/navigation";
import { ChatHistory } from "@/features/chat-history";
import {
  inboxKeys,
  POLL_INTERVAL_MS,
  useConversation,
  useConversations,
  useMessages,
} from "@/features/inbox/api";
import type { Conversation, Message, PhoneNumber } from "@/features/inbox/types";
import { router } from "@/routes/router";

// --- Fixtures -------------------------------------------------------------------------------------

function conversationFixture(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: "conv1",
    type: "conversation",
    status: "open",
    channel_type: "whatsapp",
    connector_type: "meta_cloud",
    assigned_to: null,
    contact: { id: "c1", name: "Ramesh K.", phone: "+919990000001" },
    tags: [],
    phone_number_id: "pn1",
    last_message_at: "2026-08-01T10:00:00Z",
    last_message_preview: "Thanks!",
    unread_count: 0,
    window: { is_open: true, expires_at: null, last_inbound_at: null },
    row_version: 0,
    created_at: "2026-08-01T09:00:00Z",
    updated_at: "2026-08-01T10:00:00Z",
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
    content: { text: { body: "Newest message" } },
    error_code: null,
    sent_at: "2026-08-01T09:01:00Z",
    delivered_at: null,
    read_at: null,
    created_at: "2026-08-01T09:01:00Z",
    ...overrides,
  };
}

function numberFixture(overrides: Partial<PhoneNumber> = {}): PhoneNumber {
  return {
    id: "pn1",
    type: "phone_number",
    waba_id: "w1",
    channel_type: "whatsapp",
    phone_number_id: "778899001122",
    display_number: "+911111111111",
    verified_name: "Vi Support",
    quality_rating: "GREEN",
    messaging_tier: "TIER_10K",
    throughput_level: "STANDARD",
    mps_limit: 80,
    status: "connected",
    is_default: false,
    last_synced_at: "2026-07-22T09:00:00Z",
    created_at: "2026-07-01T10:00:00Z",
    row_version: 1,
    ...overrides,
  };
}

// --- Harness ------------------------------------------------------------------------------------

const permissions = { value: ["inbox:read", "audit:read"] };

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

type ResponseEntry = unknown | ((query: Record<string, unknown> | undefined) => unknown);

/** Canned responses per path; a function entry can answer differently per query (pagination/filters). */
const responses: Record<string, ResponseEntry> = {};
const errors: Record<string, unknown> = {};
const calls: { path: string; query?: Record<string, unknown> }[] = [];

function lastCall(path: string): { path: string; query?: Record<string, unknown> } | undefined {
  return [...calls].reverse().find((call) => call.path === path);
}

vi.mock("@/lib/api/client", () => {
  const GET = async (
    path: string,
    options?: { params?: { query?: Record<string, unknown> } },
  ) => {
    calls.push({ path, query: options?.params?.query });
    if (path in errors) return { error: errors[path] };
    if (!(path in responses)) return { error: new Error(`no stub for ${path}`) };
    const entry = responses[path];
    const data = typeof entry === "function" ? (entry as (q?: Record<string, unknown>) => unknown)(options?.params?.query) : entry;
    return { data };
  };
  const write = async () => ({ error: new Error("writes are disabled in Chat History tests") });
  return {
    api: { GET, POST: write, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

/** The real Live Chat destination, reduced to what proves the deep link landed correctly. */
function InboxRouteStub(): JSX.Element {
  const [params] = useSearchParams();
  return <div data-testid="inbox-stub">Live Chat — conversation={params.get("conversation")}</div>;
}

function withProviders(ui: ReactElement, initialEntries: string[] = ["/chat-history"]) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const result = render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/chat-history" element={ui} />
          <Route path="/inbox" element={<InboxRouteStub />} />
          <Route path="/admin/audit" element={<div>Audit Trail Stub</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  // Exposed so polling/cache tests can inspect the real registered query options rather than
  // guessing at timing.
  return { ...result, client };
}

/** Forces the narrow (`isNarrow`) or desktop branch of the route's own `lg`-width media query. */
function stubViewport(narrow: boolean): void {
  vi.stubGlobal("matchMedia", (query: string) => ({
    matches: narrow && query.includes("max-width"),
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}

function seedBaseline(): void {
  responses["/api/v1/users"] = {
    data: [{ id: "u1", full_name: "Agent One", email: "agent1@example.test", is_superuser: false }],
  };
  responses["/api/v1/phone-numbers"] = { data: [numberFixture()] };
  // `useTags` (customer-profile/api.ts) returns the raw array — no `{ data }` envelope, unlike
  // `/users` and `/phone-numbers`.
  responses["/api/v1/tags"] = [{ id: "t1", name: "VIP", color: "#22c55e" }];
}

/**
 * `Query.options` is typed at the base `QueryOptions` level, which does not statically carry
 * `refetchInterval` (that's layered on by the `useQuery`/`useInfiniteQuery` hook types) — but the
 * value genuinely is set on the live, registered query at runtime, which is exactly what these
 * tests need to inspect.
 */
function refetchIntervalOf(query: { options: unknown } | undefined): unknown {
  return (query?.options as { refetchInterval?: unknown } | undefined)?.refetchInterval;
}

function findRouteByPath(node: unknown, targetPath: string): { element?: ReactElement } | null {
  const candidate = node as { path?: string; children?: unknown[]; element?: ReactElement } | null;
  if (!candidate) return null;
  if (candidate.path === targetPath) return candidate;
  for (const child of candidate.children ?? []) {
    const found = findRouteByPath(child, targetPath);
    if (found) return found;
  }
  return null;
}

beforeEach(() => {
  permissions.value = ["inbox:read", "audit:read"];
  for (const key of Object.keys(responses)) delete responses[key];
  for (const key of Object.keys(errors)) delete errors[key];
  calls.length = 0;
  seedBaseline();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// --- Tests ----------------------------------------------------------------------------------------

describe("ChatHistory", () => {
  it("1. shows the loading state before the conversation list resolves", () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    expect(screen.getByText("Loading conversation history…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("2. shows the empty state when there is no conversation history", async () => {
    responses["/api/v1/conversations"] = { data: [], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    expect(await screen.findByText("No conversation history yet")).toBeInTheDocument();
  });

  it("3. shows a list error with retry, and recovers after retry", async () => {
    errors["/api/v1/conversations"] = new Error("Conversations unavailable");
    withProviders(<ChatHistory />);

    expect(await screen.findByRole("alert")).toHaveTextContent("Conversations unavailable");

    delete errors["/api/v1/conversations"];
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Ramesh K.")).toBeInTheDocument();
  });

  it("4. lists conversations with contact, preview, status and tags", async () => {
    responses["/api/v1/conversations"] = {
      data: [
        conversationFixture({
          tags: [{ id: "t1", name: "VIP", color: "#22c55e" }],
        }),
      ],
      page: { limit: 25, has_more: false },
    };
    withProviders(<ChatHistory />);

    expect(await screen.findByText("Ramesh K.")).toBeInTheDocument();
    expect(screen.getByText("Thanks!")).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Conversation history" })).getByText("Open")).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Conversation history" })).getByText("VIP")).toBeInTheDocument();
  });

  it("5. selecting a conversation loads and shows its messages", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    expect(await screen.findByText("Newest message")).toBeInTheDocument();
  });

  it("6. shows a message error with retry, and recovers after retry", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    errors["/api/v1/conversations/{conversation_id}/messages"] = new Error("Messages unavailable");
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Messages unavailable");

    delete errors["/api/v1/conversations/{conversation_id}/messages"];
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByText("Newest message")).toBeInTheDocument();
  });

  it("7. progresses the conversation list cursor when Next is clicked", async () => {
    responses["/api/v1/conversations"] = (query: Record<string, unknown> | undefined) =>
      query?.cursor
        ? { data: [conversationFixture({ id: "conv2", contact: { id: "c2", name: "Second Contact", phone: "+919990000002" } })], page: { limit: 25, has_more: false, next_cursor: null } }
        : { data: [conversationFixture()], page: { limit: 25, has_more: true, next_cursor: "ccur2" } };
    withProviders(<ChatHistory />);

    expect(await screen.findByText("Ramesh K.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByText("Second Contact")).toBeInTheDocument();
    expect(lastCall("/api/v1/conversations")?.query?.cursor).toBe("ccur2");
  });

  it("8. loads older messages via the existing infinite-query control", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = (query: Record<string, unknown> | undefined) =>
      query?.cursor
        ? { data: [messageFixture({ id: "m0", content: { text: { body: "Older message" } } })], page: { limit: 50, has_more: false, next_cursor: null } }
        : { data: [messageFixture()], page: { limit: 50, has_more: true, next_cursor: "mcur2" } };
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    expect(await screen.findByText("Newest message")).toBeInTheDocument();
    expect(screen.queryByText("Older message")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Load older messages" }));
    expect(await screen.findByText("Older message")).toBeInTheDocument();
  });

  it("9. maps the search box to the q filter", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    await screen.findByText("Ramesh K.");

    fireEvent.change(screen.getByLabelText("Search chat history"), { target: { value: "ramesh" } });
    await waitFor(() => expect(lastCall("/api/v1/conversations")?.query?.q).toBe("ramesh"));
  });

  it("10. maps the status select to the status filter", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    await screen.findByText("Ramesh K.");

    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "resolved" } });
    await waitFor(() => expect(lastCall("/api/v1/conversations")?.query?.status).toBe("resolved"));
  });

  it("11. maps the assignee select to the assignee filter", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    await screen.findByText("Ramesh K.");

    fireEvent.change(screen.getByLabelText("Agent"), { target: { value: "u1" } });
    await waitFor(() => expect(lastCall("/api/v1/conversations")?.query?.assignee).toBe("u1"));
  });

  it("12. maps the number select to the number filter", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    await screen.findByText("Ramesh K.");

    fireEvent.change(screen.getByLabelText("Channel"), { target: { value: "pn1" } });
    await waitFor(() => expect(lastCall("/api/v1/conversations")?.query?.number).toBe("pn1"));
  });

  it("13. maps a tag chip to the tag filter", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    await screen.findByText("Ramesh K.");

    fireEvent.click(screen.getByRole("button", { name: "VIP" }));
    await waitFor(() => expect(lastCall("/api/v1/conversations")?.query?.tag).toEqual(["t1"]));
  });

  it("14. shows a no-results state for a filter with no matches, and Clear filters resets it", async () => {
    responses["/api/v1/conversations"] = (query: Record<string, unknown> | undefined) =>
      query?.q === "nomatch"
        ? { data: [], page: { limit: 25, has_more: false } }
        : { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);
    await screen.findByText("Ramesh K.");

    fireEvent.change(screen.getByLabelText("Search chat history"), { target: { value: "nomatch" } });
    expect(await screen.findByText("No conversations match")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(await screen.findByText("Ramesh K.")).toBeInTheDocument();
    expect(screen.getByLabelText("Search chat history")).toHaveValue("");
  });

  it("15. deep-links the selected conversation into Live Chat", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = { data: [], page: { limit: 50, has_more: false } };
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    fireEvent.click(await screen.findByRole("button", { name: "Open in Live Chat" }));

    expect(await screen.findByTestId("inbox-stub")).toHaveTextContent("conversation=conv1");
  });

  it("16. shows the audit trail link with audit:read", async () => {
    responses["/api/v1/conversations"] = { data: [], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);

    const auditLink = await screen.findByRole("button", { name: "Open audit trail" });
    fireEvent.click(auditLink);
    expect(await screen.findByText("Audit Trail Stub")).toBeInTheDocument();
  });

  it("17. hides the audit trail link without audit:read", async () => {
    permissions.value = ["inbox:read"];
    responses["/api/v1/conversations"] = { data: [], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);

    await screen.findByText("No conversation history yet");
    expect(screen.queryByRole("button", { name: "Open audit trail" })).not.toBeInTheDocument();
  });

  it("18. exposes no composer or write action for a selected conversation", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    await screen.findByText("Newest message");

    expect(screen.queryByRole("textbox", { name: /message/i })).not.toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/type a message/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Send$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /assign/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /change status/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add (a )?note/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add label/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /react to message/i })).not.toBeInTheDocument();
  });

  it("19. gates the route and navigation entry on inbox:read", () => {
    const navEntry = navItems.find((item) => item.path === "/chat-history");
    expect(navEntry?.permission).toBe("inbox:read");

    const routeEntry = findRouteByPath({ children: router.routes }, "chat-history");
    expect((routeEntry?.element as ReactElement | undefined)?.props).toMatchObject({
      code: "inbox:read",
    });
  });

  it("20. shares the conversation-list cache with the existing inbox hook, not a second query", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };

    function ConversationsProbe(): JSX.Element {
      const conversations = useConversations({}, null, 25);
      return <div data-testid="probe">{conversations.data?.data.length ?? 0}</div>;
    }

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={["/chat-history"]}>
          <Routes>
            <Route
              path="/chat-history"
              element={
                <>
                  <ChatHistory />
                  <ConversationsProbe />
                </>
              }
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("Ramesh K.");
    await waitFor(() => expect(screen.getByTestId("probe")).toHaveTextContent("1"));
    expect(calls.filter((call) => call.path === "/api/v1/conversations").length).toBe(1);
  });

  it("21. never fetches an unbounded page of conversations or messages", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: true, next_cursor: "ccur2" } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: true, next_cursor: "mcur2" },
    };
    withProviders(<ChatHistory />);

    await screen.findByText("Ramesh K.");
    expect(lastCall("/api/v1/conversations")?.query?.limit).toBe(25);

    fireEvent.click(screen.getByRole("button", { name: /Ramesh K\./ }));
    await screen.findByText("Newest message");
    expect(lastCall("/api/v1/conversations/{conversation_id}/messages")?.query?.limit).toBe(50);
    // Having more available never auto-fetches a further page on its own.
    expect(calls.filter((call) => call.path === "/api/v1/conversations/{conversation_id}/messages").length).toBe(1);
  });

  it("22. keeps list selection, controls and errors accessible", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = { data: [], page: { limit: 50, has_more: false } };
    withProviders(<ChatHistory />);

    expect(await screen.findByLabelText("Search chat history")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Conversation history pagination" })).toBeInTheDocument();

    const row = await screen.findByRole("button", { name: /Ramesh K\./ });
    expect(row).not.toHaveAttribute("aria-current");
    fireEvent.click(row);
    await waitFor(() => expect(row).toHaveAttribute("aria-current", "true"));
  });

  it("makes no conversation-detail or message request until a conversation is selected", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />);

    await screen.findByText("Ramesh K.");
    expect(calls.some((call) => call.path === "/api/v1/conversations/{conversation_id}")).toBe(false);
    expect(
      calls.some((call) => call.path === "/api/v1/conversations/{conversation_id}/messages"),
    ).toBe(false);
  });

  // --- D1: dead Previous control replaced with a bounded forward-only reset ---------------------

  it("D1. removes the dead Previous control and offers Back to newest only after paging forward", async () => {
    responses["/api/v1/conversations"] = (query: Record<string, unknown> | undefined) =>
      query?.cursor
        ? {
            data: [
              conversationFixture({
                id: "conv2",
                contact: { id: "c2", name: "Second Contact", phone: "+919990000002" },
              }),
            ],
            page: { limit: 25, has_more: false, next_cursor: null },
          }
        : { data: [conversationFixture()], page: { limit: 25, has_more: true, next_cursor: "ccur2" } };
    withProviders(<ChatHistory />);

    expect(await screen.findByText("Ramesh K.")).toBeInTheDocument();
    // No bidirectional pagination affordance — the backend never returns `prev_cursor`.
    expect(screen.queryByRole("button", { name: /^previous$/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Back to newest" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    expect(await screen.findByText("Second Contact")).toBeInTheDocument();
    expect(lastCall("/api/v1/conversations")?.query?.cursor).toBe("ccur2");
    expect(lastCall("/api/v1/conversations")?.query?.limit).toBe(25);

    const backToNewest = await screen.findByRole("button", { name: "Back to newest" });
    fireEvent.click(backToNewest);

    expect(await screen.findByText("Ramesh K.")).toBeInTheDocument();
    expect(screen.queryByText("Second Contact")).not.toBeInTheDocument();
    await waitFor(() => expect(lastCall("/api/v1/conversations")?.query?.cursor).toBeNull());
    // Reloading the initial page is still exactly one bounded 25-row page, not every page fetched.
    expect(lastCall("/api/v1/conversations")?.query?.limit).toBe(25);
    expect(screen.queryByRole("button", { name: "Back to newest" })).not.toBeInTheDocument();
  });

  // --- D2: no background polling for a read-only history selection ------------------------------

  it("D2. disables polling for the selected conversation's detail and its messages", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    const { client } = withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    await screen.findByText("Newest message");

    await waitFor(() => {
      const detail = client.getQueryCache().find({ queryKey: inboxKeys.detail("conv1") });
      expect(refetchIntervalOf(detail)).toBe(false);
    });
    const messagesQuery = client.getQueryCache().find({ queryKey: inboxKeys.messages("conv1") });
    expect(refetchIntervalOf(messagesQuery)).toBe(false);
  });

  it("D2. preserves the shared hook's 10s poll default for consumers that pass no override", async () => {
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };

    // The same call shape Live Chat's ConversationThread and Customer 360's
    // ConversationHistorySection already make — no third argument.
    function DefaultConsumerProbe(): JSX.Element {
      useConversation("conv1");
      useMessages("conv1");
      return <div data-testid="default-probe" />;
    }

    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <DefaultConsumerProbe />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      const detail = client.getQueryCache().find({ queryKey: inboxKeys.detail("conv1") });
      expect(refetchIntervalOf(detail)).toBe(POLL_INTERVAL_MS);
    });
    const messagesQuery = client.getQueryCache().find({ queryKey: inboxKeys.messages("conv1") });
    expect(refetchIntervalOf(messagesQuery)).toBe(POLL_INTERVAL_MS);
  });

  it("D2. loading an older message page does not reactivate polling", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = (query: Record<string, unknown> | undefined) =>
      query?.cursor
        ? { data: [messageFixture({ id: "m0", content: { text: { body: "Older message" } } })], page: { limit: 50, has_more: false, next_cursor: null } }
        : { data: [messageFixture()], page: { limit: 50, has_more: true, next_cursor: "mcur2" } };
    const { client } = withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    await screen.findByText("Newest message");
    fireEvent.click(screen.getByRole("button", { name: "Load older messages" }));
    await screen.findByText("Older message");

    const messagesQuery = client.getQueryCache().find({ queryKey: inboxKeys.messages("conv1") });
    expect(refetchIntervalOf(messagesQuery)).toBe(false);
  });

  // --- D3: focus follows the visible pane on narrow viewports only ------------------------------

  it("D3. moves focus into the detail pane after selecting a conversation on a narrow viewport", async () => {
    stubViewport(true);
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Back to conversation history" })).toHaveFocus(),
    );
  });

  it("D3. restores focus to the previously selected row when returning to the list on a narrow viewport", async () => {
    stubViewport(true);
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    const backButton = await screen.findByRole("button", { name: "Back to conversation history" });
    await waitFor(() => expect(backButton).toHaveFocus());

    fireEvent.click(backButton);

    const row = await screen.findByRole("button", { name: /Ramesh K\./ });
    await waitFor(() => expect(row).toHaveFocus());
  });

  it("D3. does not force focus movement on desktop viewports", async () => {
    stubViewport(false);
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    withProviders(<ChatHistory />);

    const row = await screen.findByRole("button", { name: /Ramesh K\./ });
    // Simulates the realistic pre-click state a keyboard/mouse user leaves behind — fireEvent.click
    // itself does not move focus, so this isolates whether the component's own effect does.
    row.focus();
    expect(row).toHaveFocus();

    fireEvent.click(row);
    await screen.findByText("Newest message");

    expect(row).toHaveFocus();
    expect(screen.getByRole("button", { name: "Back to conversation history" })).not.toHaveFocus();
  });

  // --- D4: the contact deep-link filter participates in active-filter detection -----------------

  it("D4. shows the no-results state (with Clear filters) for a contact filter with no matches", async () => {
    responses["/api/v1/conversations"] = (query: Record<string, unknown> | undefined) =>
      query?.contact === "c-404"
        ? { data: [], page: { limit: 25, has_more: false } }
        : { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    withProviders(<ChatHistory />, ["/chat-history?contact=c-404"]);

    expect(lastCall("/api/v1/conversations")?.query?.contact).toBe("c-404");
    expect(await screen.findByText("No conversations match")).toBeInTheDocument();
    expect(screen.queryByText("No conversation history yet")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));

    expect(await screen.findByText("Ramesh K.")).toBeInTheDocument();
    await waitFor(() => expect(lastCall("/api/v1/conversations")?.query?.contact).toBeNull());
  });

  // --- D6: status badge tone matches Live Chat's open-only success convention -------------------

  it("D6. colors the status badge success only for open conversations", async () => {
    responses["/api/v1/conversations"] = {
      data: [
        conversationFixture({
          id: "c-open",
          status: "open",
          contact: { id: "c1", name: "Open Contact", phone: "+910000000001" },
        }),
        conversationFixture({
          id: "c-pending",
          status: "pending",
          contact: { id: "c2", name: "Pending Contact", phone: "+910000000002" },
        }),
        conversationFixture({
          id: "c-resolved",
          status: "resolved",
          contact: { id: "c3", name: "Resolved Contact", phone: "+910000000003" },
        }),
        conversationFixture({
          id: "c-snoozed",
          status: "snoozed",
          contact: { id: "c4", name: "Snoozed Contact", phone: "+910000000004" },
        }),
      ],
      page: { limit: 25, has_more: false },
    };
    withProviders(<ChatHistory />);

    await screen.findByText("Open Contact");
    const list = screen.getByRole("list", { name: "Conversation history" });

    expect(within(list).getByText("Open").closest("span")).toHaveClass("bg-success-soft");
    expect(within(list).getByText("Pending").closest("span")).toHaveClass("bg-surface-2");
    expect(within(list).getByText("Resolved").closest("span")).toHaveClass("bg-surface-2");
    expect(within(list).getByText("Snoozed").closest("span")).toHaveClass("bg-surface-2");
  });

  // --- D7: the message list has an accessible name -----------------------------------------------

  it("D7. names the message list for assistive technology", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    withProviders(<ChatHistory />);

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    expect(await screen.findByRole("list", { name: "Message history" })).toBeInTheDocument();
  });

  // --- D8: semantic, non-duplicated headings ------------------------------------------------------

  it("D8. uses a page-level heading and a heading for the selected thread", async () => {
    responses["/api/v1/conversations"] = { data: [conversationFixture()], page: { limit: 25, has_more: false } };
    responses["/api/v1/conversations/{conversation_id}"] = conversationFixture();
    responses["/api/v1/conversations/{conversation_id}/messages"] = {
      data: [messageFixture()],
      page: { limit: 50, has_more: false },
    };
    withProviders(<ChatHistory />);

    expect(screen.getByRole("heading", { level: 1, name: "Chat History" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2 })).not.toBeInTheDocument();

    fireEvent.click(await screen.findByRole("button", { name: /Ramesh K\./ }));
    expect(await screen.findByRole("heading", { level: 2, name: "Ramesh K." })).toBeInTheDocument();
  });
});
