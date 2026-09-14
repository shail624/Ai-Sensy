import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { visibleNavItems } from "@/components/layout/navigation";
import {
  HealthChip,
  NumberStatusChip,
  QualityChip,
  TokenChip,
  WabaStatusChip,
} from "@/features/channels/ChannelBadges";
import { NumberActions } from "@/features/channels/NumberActions";
import { NumberEditDialog } from "@/features/channels/NumberEditDialog";
import { NumberList } from "@/features/channels/NumberList";
import { buildWhatsAppChatLink } from "@/features/channels/WhatsAppChatLinkDialog";
import {
  filterNumbers,
  filterWabas,
  matchesNumber,
  matchesWaba,
  numberStatuses,
  numberSummary,
  numbersForWaba,
  selectNumbers,
  selectWabas,
  wabaSummary,
} from "@/features/channels/selectors";
import { WabaActions } from "@/features/channels/WabaActions";
import { WabaList } from "@/features/channels/WabaList";
import {
  buildWhatsAppOverview,
  WhatsAppOverview,
} from "@/features/channels/WhatsAppOverview";
import type {
  NumberListQuery,
  PhoneNumber,
  Waba,
  WabaListQuery,
} from "@/features/channels/types";
import {
  DEFAULT_NUMBER_QUERY,
  DEFAULT_WABA_QUERY,
  isDisconnectable,
  isNumberHealthy,
  isReactivatable,
  tokenState,
} from "@/features/channels/types";

// --- Fixtures -----------------------------------------------------------------------------------

function wabaFixture(overrides: Partial<Waba> = {}): Waba {
  return {
    id: "w1",
    type: "waba",
    waba_id: "102938475610293",
    business_name: "Vi Reactivation",
    meta_business_id: "555000111",
    currency: "INR",
    timezone: "Asia/Kolkata",
    status: "active",
    token_set: true,
    token_expires_at: null,
    phone_number_count: 2,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    row_version: 3,
    ...overrides,
  };
}

function numberFixture(overrides: Partial<PhoneNumber> = {}): PhoneNumber {
  return {
    id: "n1",
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

const permissions = { value: ["waba:read", "waba:manage"] };

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

vi.mock("qrcode", () => ({
  toDataURL: vi.fn(async () => "data:image/png;base64,local-qr"),
}));

/** Canned responses per path, so the real hooks and components run without a network. */
const responses: Record<string, unknown> = {};

vi.mock("@/lib/api/client", () => {
  const get = async (path: string) =>
    path in responses ? { data: responses[path] } : { error: new Error(`no stub for ${path}`) };
  const write = async () => ({ error: new Error("network disabled under test") });
  return {
    api: { GET: get, POST: write, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

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

function wabaQuery(overrides: Partial<WabaListQuery> = {}): WabaListQuery {
  return { ...DEFAULT_WABA_QUERY, ...overrides };
}

function numberQuery(overrides: Partial<NumberListQuery> = {}): NumberListQuery {
  return { ...DEFAULT_NUMBER_QUERY, ...overrides };
}

beforeEach(() => {
  permissions.value = ["waba:read", "waba:manage"];
  for (const key of Object.keys(responses)) delete responses[key];
});

// --- Token state ---------------------------------------------------------------------------------

describe("tokenState", () => {
  const now = Date.parse("2026-07-23T00:00:00Z");

  it("reports a missing credential", () => {
    expect(tokenState(wabaFixture({ token_set: false }), now)).toBe("missing");
  });

  it("distinguishes a stored token from a usable one", () => {
    // `token_set` is true either way — an expired token is still stored, and would fail at the
    // next Meta call, so "set" and "usable" cannot be the same badge.
    expect(tokenState(wabaFixture({ token_expires_at: "2026-07-01T00:00:00Z" }), now)).toBe(
      "expired",
    );
    expect(tokenState(wabaFixture({ token_expires_at: "2026-07-28T00:00:00Z" }), now)).toBe(
      "expiring",
    );
    expect(tokenState(wabaFixture({ token_expires_at: "2027-01-01T00:00:00Z" }), now)).toBe("ok");
  });

  it("treats no recorded expiry as fine, because nothing says otherwise", () => {
    expect(tokenState(wabaFixture({ token_expires_at: null }), now)).toBe("ok");
  });
});

// --- Lifecycle rules -------------------------------------------------------------------------------

describe("lifecycle rules", () => {
  it("refuses to disconnect an account that still owns numbers", () => {
    expect(isDisconnectable(wabaFixture({ phone_number_count: 2 }))).toBe(false);
    expect(isDisconnectable(wabaFixture({ phone_number_count: 0 }))).toBe(true);
  });

  it("offers reactivation only to an account that is not already active", () => {
    expect(isReactivatable(wabaFixture({ status: "active" }))).toBe(false);
    expect(isReactivatable(wabaFixture({ status: "suspended" }))).toBe(true);
    expect(isReactivatable(wabaFixture({ status: "disabled" }))).toBe(true);
  });

  it("calls a number healthy only when connected and not rated RED", () => {
    expect(isNumberHealthy(numberFixture())).toBe(true);
    expect(isNumberHealthy(numberFixture({ quality_rating: "RED" }))).toBe(false);
    expect(isNumberHealthy(numberFixture({ status: "pending" }))).toBe(false);
    // Unrated is not unhealthy — Meta simply has not rated it yet.
    expect(isNumberHealthy(numberFixture({ quality_rating: null }))).toBe(true);
  });
});

// --- WABA selectors --------------------------------------------------------------------------------

describe("selectors — WABAs", () => {
  const rows = [
    wabaFixture({ id: "a", business_name: "Alpha", waba_id: "111", status: "active", phone_number_count: 1, created_at: "2026-07-01T00:00:00Z" }),
    wabaFixture({ id: "b", business_name: "Bravo", waba_id: "222", status: "suspended", phone_number_count: 5, created_at: "2026-07-02T00:00:00Z" }),
  ];

  it("searches the business name, the WABA id and the Meta business id", () => {
    expect(matchesWaba(rows[0]!, "alph")).toBe(true);
    expect(matchesWaba(rows[1]!, "222")).toBe(true);
    expect(matchesWaba(rows[0]!, "555000")).toBe(true);
    expect(matchesWaba(rows[0]!, "nothing")).toBe(false);
  });

  it("filters by status", () => {
    expect(filterWabas(rows, wabaQuery({ status: "suspended" })).map((r) => r.id)).toEqual(["b"]);
  });

  it("sorts by name, recency and number count", () => {
    expect(selectWabas(rows, wabaQuery({ sort: "-name" })).map((r) => r.id)).toEqual(["b", "a"]);
    expect(selectWabas(rows, wabaQuery({ sort: "-created_at" })).map((r) => r.id)).toEqual(["b", "a"]);
    expect(selectWabas(rows, wabaQuery({ sort: "-numbers" })).map((r) => r.id)).toEqual(["b", "a"]);
  });

  it("counts accounts whose credential needs attention", () => {
    const now = Date.parse("2026-07-23T00:00:00Z");
    const summary = wabaSummary(
      [
        wabaFixture({ status: "active" }),
        wabaFixture({ status: "suspended", token_set: false, phone_number_count: 1 }),
        wabaFixture({ token_expires_at: "2026-07-01T00:00:00Z", phone_number_count: 3 }),
      ],
      now,
    );
    expect(summary).toEqual({ total: 3, active: 2, needsAttention: 2, numbers: 6 });
  });
});

// --- Phone-number selectors --------------------------------------------------------------------------

describe("selectors — phone numbers", () => {
  const rows = [
    numberFixture({ id: "a", display_number: "+911", quality_rating: "GREEN", waba_id: "w1", mps_limit: 20 }),
    numberFixture({ id: "b", display_number: "+922", quality_rating: "RED", waba_id: "w2", mps_limit: 80, status: "flagged" }),
    numberFixture({ id: "c", display_number: "+933", quality_rating: null, waba_id: "w1", mps_limit: 50 }),
  ];

  it("searches the number, the display name and Meta's id", () => {
    expect(matchesNumber(rows[0]!, "911")).toBe(true);
    expect(matchesNumber(rows[0]!, "vi sup")).toBe(true);
    expect(matchesNumber(rows[0]!, "778899")).toBe(true);
  });

  it("filters by account, status and quality independently", () => {
    expect(filterNumbers(rows, numberQuery({ waba: "w1" })).map((r) => r.id)).toEqual(["a", "c"]);
    expect(filterNumbers(rows, numberQuery({ status: "flagged" })).map((r) => r.id)).toEqual(["b"]);
    expect(filterNumbers(rows, numberQuery({ quality: "RED" })).map((r) => r.id)).toEqual(["b"]);
  });

  it("sorts the worst quality first, with unrated numbers last", () => {
    // Absent is not "good" — an unrated number must not be ranked alongside GREEN.
    expect(selectNumbers(rows, numberQuery({ sort: "-quality" })).map((r) => r.id)).toEqual([
      "b",
      "a",
      "c",
    ]);
  });

  it("sorts by pacing limit", () => {
    expect(selectNumbers(rows, numberQuery({ sort: "-mps_limit" })).map((r) => r.id)).toEqual([
      "b",
      "c",
      "a",
    ]);
  });

  it("summarises capacity over connected numbers only", () => {
    // The flagged number's 80/s is not capacity the platform actually has.
    expect(numberSummary(rows)).toEqual({
      total: 3,
      connected: 2,
      healthy: 2,
      degraded: 1,
      capacity: 70,
    });
  });

  it("always offers 'connected' as a status option, plus whatever Meta wrote", () => {
    expect(numberStatuses(rows)).toEqual(["connected", "flagged"]);
    expect(numberStatuses([])).toEqual(["connected"]);
  });

  it("groups numbers by their owning account", () => {
    expect(numbersForWaba(rows, "w1").map((r) => r.id)).toEqual(["a", "c"]);
  });
});

// --- Dashboard overview -----------------------------------------------------------------------------

describe("WhatsAppOverview", () => {
  it("derives readiness from the existing account and number contracts", () => {
    const account = wabaFixture();
    const number = numberFixture({ is_default: true });

    expect(buildWhatsAppOverview([account], [number])).toMatchObject({
      account,
      number,
      accountReady: true,
      numberReady: true,
      channelReady: true,
      qualityLabel: "High",
      completedSteps: 3,
    });
  });

  it("does not present a degraded channel as ready", () => {
    expect(
      buildWhatsAppOverview(
        [wabaFixture({ token_set: false })],
        [numberFixture({ quality_rating: "RED" })],
      ),
    ).toMatchObject({
      accountReady: false,
      numberReady: true,
      channelReady: false,
      qualityLabel: "Low",
      completedSteps: 1,
    });
  });

  it("renders real channel identity, quality and capacity with governed routes", async () => {
    responses["/api/v1/waba"] = { data: [wabaFixture()] };
    responses["/api/v1/phone-numbers"] = { data: [numberFixture({ is_default: true })] };
    withProviders(<WhatsAppOverview />);

    const overview = await screen.findByRole("region", { name: "WhatsApp overview" });
    expect(within(overview).getByText("3 of 3 ready")).toBeInTheDocument();
    expect(within(overview).getAllByText("High").length).toBeGreaterThan(0);
    expect(within(overview).getByText("80/sec")).toBeInTheDocument();
    expect(within(overview).getAllByText("Vi Reactivation").length).toBeGreaterThan(0);
    expect(within(overview).getByRole("link", { name: /manage/i })).toHaveAttribute(
      "href",
      "/channels/accounts",
    );
    expect(within(overview).getByRole("link", { name: /review channel health/i })).toHaveAttribute(
      "href",
      "/channels/numbers/n1",
    );
  });

  it("guides an unconnected workspace without fabricating commercial data", async () => {
    responses["/api/v1/waba"] = { data: [] };
    responses["/api/v1/phone-numbers"] = { data: [] };
    withProviders(<WhatsAppOverview />);

    const overview = await screen.findByRole("region", { name: "WhatsApp overview" });
    expect(within(overview).getByText("0 of 3 ready")).toBeInTheDocument();
    expect(within(overview).getByText("No business account connected")).toBeInTheDocument();
    expect(within(overview).getByRole("link", { name: /connect business account/i })).toHaveAttribute(
      "href",
      "/channels/accounts",
    );
    expect(within(overview).queryByText(/credit|plan|quota/i)).not.toBeInTheDocument();
  });
});

// --- Badges ------------------------------------------------------------------------------------------

describe("ChannelBadges", () => {
  it("labels WABA statuses and passes unknown ones through verbatim", () => {
    withProviders(
      <>
        <WabaStatusChip value="suspended" />
        <WabaStatusChip value="some_new_state" />
      </>,
    );
    expect(screen.getByText("Suspended")).toBeInTheDocument();
    expect(screen.getByText("some_new_state")).toBeInTheDocument();
  });

  it("says a missing quality rating is 'not rated', not bad", () => {
    withProviders(<QualityChip value={null} />);
    expect(screen.getByText("Not rated")).toBeInTheDocument();
  });

  it("reports credential health separately from the status", () => {
    withProviders(<TokenChip waba={wabaFixture({ token_set: false })} />);
    expect(screen.getByText("No token")).toBeInTheDocument();
  });

  it("renders the health verdict", () => {
    withProviders(
      <>
        <HealthChip healthy />
        <NumberStatusChip value="connected" />
      </>,
    );
    expect(screen.getByText("Healthy")).toBeInTheDocument();
    expect(screen.getByText("connected")).toBeInTheDocument();
  });
});

// --- Actions -----------------------------------------------------------------------------------------

describe("WabaActions", () => {
  it("offers sync but not reactivation for an active account", () => {
    withProviders(<WabaActions waba={wabaFixture({ status: "active" })} />);
    expect(screen.getByRole("button", { name: "Sync numbers" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reactivate" })).not.toBeInTheDocument();
  });

  it("offers reactivation for a suspended account", () => {
    withProviders(<WabaActions waba={wabaFixture({ status: "suspended" })} />);
    expect(screen.getByRole("button", { name: "Reactivate" })).toBeInTheDocument();
  });

  it("explains why an account with numbers cannot be disconnected", () => {
    withProviders(<WabaActions waba={wabaFixture({ phone_number_count: 2 })} />);
    expect(screen.queryByRole("button", { name: "Disconnect" })).not.toBeInTheDocument();
    expect(screen.getByText(/cannot be disconnected/)).toBeInTheDocument();
  });

  it("warns that a disconnect cannot be undone before doing it", () => {
    withProviders(<WabaActions waba={wabaFixture({ phone_number_count: 0 })} />);
    fireEvent.click(screen.getByRole("button", { name: "Disconnect" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByText(/cannot be connected again here/)).toBeInTheDocument();
  });

  it("hides every write control from a read-only operator", () => {
    permissions.value = ["waba:read"];
    withProviders(<WabaActions waba={wabaFixture({ status: "suspended", phone_number_count: 0 })} />);
    expect(screen.queryByRole("button", { name: "Sync numbers" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reactivate" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Disconnect" })).not.toBeInTheDocument();
  });
});

describe("NumberActions", () => {
  it("offers refresh and edit to a manager", () => {
    withProviders(<NumberActions number={numberFixture()} />);
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chat link & QR" })).toBeInTheDocument();
  });

  it("leaves edit to the detail page in compact rows", () => {
    withProviders(<NumberActions number={numberFixture()} compact />);
    expect(screen.getByRole("button", { name: "Refresh" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Chat link & QR" })).not.toBeInTheDocument();
  });

  it("hides every write control from a read-only operator", () => {
    permissions.value = ["waba:read"];
    withProviders(<NumberActions number={numberFixture()} />);
    expect(screen.queryByRole("button", { name: "Refresh" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Chat link & QR" })).toBeInTheDocument();
  });
});

describe("WhatsApp chat link and QR", () => {
  it("builds a public click-to-chat URL from a formatted international number", () => {
    expect(buildWhatsAppChatLink("+91 (111) 111-1111", "Hello there")).toBe(
      "https://wa.me/911111111111?text=Hello+there",
    );
    expect(buildWhatsAppChatLink("invalid", "Hello")).toBeNull();
  });

  it("opens an offline-generated QR without requiring a write permission", async () => {
    permissions.value = ["waba:read"];
    withProviders(<NumberActions number={numberFixture()} />);

    fireEvent.click(screen.getByRole("button", { name: "Chat link & QR" }));
    const dialog = screen.getByRole("dialog", { name: /Chat link for/ });
    expect(within(dialog).getByLabelText("Shareable link")).toHaveValue(
      "https://wa.me/911111111111",
    );
    expect(
      await within(dialog).findByAltText(/QR code opening a WhatsApp chat/),
    ).toHaveAttribute("src", "data:image/png;base64,local-qr");
    expect(within(dialog).getByText(/does not upload/)).toBeInTheDocument();
  });
});

describe("NumberEditDialog", () => {
  it("offers only the three operator-owned fields, and says why", () => {
    withProviders(<NumberEditDialog number={numberFixture()} onClose={vi.fn()} />);
    expect(screen.getByLabelText("Display name")).toBeInTheDocument();
    expect(screen.getByLabelText(/Send pacing/)).toBeInTheDocument();
    expect(screen.getByText(/set by Meta and cannot be edited here/)).toBeInTheDocument();
  });

  it("bounds the pacing limit to what the server accepts", () => {
    withProviders(<NumberEditDialog number={numberFixture()} onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText(/Send pacing/), { target: { value: "5000" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(screen.getByText(/between 1 and 1000/)).toBeInTheDocument();
  });
});

// --- Lists (real hooks, stubbed transport) ------------------------------------------------------------

describe("WabaList", () => {
  it("lists accounts with their status and credential health", async () => {
    responses["/api/v1/waba"] = { data: [wabaFixture({ business_name: "Vi Reactivation" })] };
    withProviders(<WabaList />);

    expect(await screen.findByRole("link", { name: "Vi Reactivation" })).toHaveAttribute(
      "href",
      "/channels/accounts/w1",
    );
    const row = screen
      .getAllByRole("row")
      .find((entry) => within(entry).queryByText("Vi Reactivation"))!;
    expect(within(row).getByText("Active")).toBeInTheDocument();
  });

  it("invites a manager to connect the first account", async () => {
    responses["/api/v1/waba"] = { data: [] };
    withProviders(<WabaList />);
    expect(await screen.findByText("No WhatsApp Business Accounts")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Connect account" })).toBeInTheDocument();
  });

  it("hides the connect control from a read-only operator", async () => {
    permissions.value = ["waba:read"];
    responses["/api/v1/waba"] = { data: [] };
    withProviders(<WabaList />);
    await screen.findByText("No WhatsApp Business Accounts");
    expect(screen.queryByRole("button", { name: "Connect account" })).not.toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<WabaList />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

describe("NumberList", () => {
  function seed(numbers: PhoneNumber[]) {
    responses["/api/v1/phone-numbers"] = { data: numbers };
    responses["/api/v1/waba"] = { data: [wabaFixture()] };
  }

  it("lists numbers with quality, tier and pacing", async () => {
    seed([numberFixture()]);
    withProviders(<NumberList />);

    expect(await screen.findByRole("link", { name: "+911111111111" })).toHaveAttribute(
      "href",
      "/channels/numbers/n1",
    );
    expect(screen.getAllByText("GREEN").length).toBeGreaterThan(0);
    expect(screen.getByText("TIER_10K")).toBeInTheDocument();
    expect(screen.getByText("80/s")).toBeInTheDocument();
  });

  it("filters by quality without a round trip", async () => {
    seed([
      numberFixture({ id: "a", display_number: "+911", quality_rating: "GREEN" }),
      numberFixture({ id: "b", display_number: "+922", quality_rating: "RED" }),
    ]);
    withProviders(<NumberList />);

    await screen.findByRole("link", { name: "+911" });
    fireEvent.change(screen.getByLabelText("Quality"), { target: { value: "RED" } });

    await waitFor(() =>
      expect(screen.queryByRole("link", { name: "+911" })).not.toBeInTheDocument(),
    );
    expect(screen.getByRole("link", { name: "+922" })).toBeInTheDocument();
  });

  it("explains that numbers come from a sync rather than offering to add one", async () => {
    seed([]);
    withProviders(<NumberList />);
    expect(await screen.findByText("No phone numbers")).toBeInTheDocument();
    expect(screen.getByText(/cannot be added by hand/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add/i })).not.toBeInTheDocument();
  });
});

// --- Navigation ----------------------------------------------------------------------------------------

describe("navigation — WhatsApp entry", () => {
  it("is visible to someone holding waba:read", () => {
    expect(visibleNavItems((code) => code === "waba:read").map((item) => item.path)).toContain(
      "/channels",
    );
  });

  it("is hidden from someone without it", () => {
    expect(visibleNavItems((code) => code === "inbox:read").map((item) => item.path)).not.toContain(
      "/channels",
    );
  });
});
