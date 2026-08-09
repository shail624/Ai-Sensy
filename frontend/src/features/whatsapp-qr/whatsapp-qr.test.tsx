import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WhatsAppQrConnect } from "@/features/whatsapp-qr/WhatsAppQrConnect";
import { whatsAppQrKeys } from "@/features/whatsapp-qr/api";
import type { WhatsAppQrStatus } from "@/features/whatsapp-qr/types";
import { deriveViewState } from "@/features/whatsapp-qr/viewState";

// --- Harness --------------------------------------------------------------------------------------

const permissions = { value: ["channels:read", "channels:authenticate"] };

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

const statusResponse = { current: null as unknown };
type MockResponse = { data?: unknown; error?: unknown };
const postHandlers: Record<string, () => MockResponse | Promise<MockResponse>> = {};
let qrBlobAvailable = true;
let qrRequestCount = 0;

vi.mock("@/lib/api/client", () => {
  const get = async (path: string, opts?: { parseAs?: string }) => {
    if (path === "/api/v1/channels/whatsapp-qr/session") {
      return statusResponse.current
        ? { data: statusResponse.current }
        : { error: new Error("no status stub") };
    }
    if (path === "/api/v1/channels/whatsapp-qr/session/qr") {
      qrRequestCount += 1;
      if (!qrBlobAvailable) return { error: new Error("qr not available") };
      if (opts?.parseAs === "blob") {
        return { data: new Blob(["fake-qr-bytes"], { type: "image/png" }) };
      }
      return { data: undefined };
    }
    return { error: new Error(`no GET stub for ${path}`) };
  };
  const post = async (path: string) => {
    const key = path.replace("/api/v1/channels/whatsapp-qr", "");
    const handler = postHandlers[key];
    return handler ? handler() : { error: new Error(`no POST stub for ${path}`) };
  };
  return {
    api: { GET: get, POST: post, PATCH: post, PUT: post, DELETE: post },
    authClient: { POST: post },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

function statusFixture(overrides: Partial<WhatsAppQrStatus> = {}): WhatsAppQrStatus {
  return {
    configured: true,
    session_public_id: "sess-1",
    row_version: 1,
    session_state: "active",
    pairing_state: "paired",
    provider_status: "WORKING",
    connected: true,
    requires_reauthentication: false,
    healthy: true,
    health_detail: "Session state: active.",
    can_reconnect: false,
    reconnect_blocked_reason: null,
    identity_masked: "9193*****553@c.us",
    push_name: "Neha Sharma",
    qr_available: false,
    provider_session_missing: false,
    updated_at: "2026-08-08T05:00:00Z",
    ...overrides,
  };
}

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const rendered = render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...rendered, client };
}

// JSDOM does not implement the Blob object-URL APIs the QR image hook uses.
let objectUrlCounter = 0;
beforeEach(() => {
  permissions.value = ["channels:read", "channels:authenticate"];
  statusResponse.current = null;
  qrBlobAvailable = true;
  qrRequestCount = 0;
  for (const key of Object.keys(postHandlers)) delete postHandlers[key];
  objectUrlCounter = 0;
  URL.createObjectURL = vi.fn(() => `blob:mock-${(objectUrlCounter += 1)}`);
  URL.revokeObjectURL = vi.fn();
});

// --- Pure state derivation: every one of the 12 required states --------------------------------

describe("deriveViewState", () => {
  it("1. not configured / unavailable", () => {
    expect(deriveViewState(undefined)).toBe("not-configured");
    expect(deriveViewState(statusFixture({ configured: false }))).toBe("not-configured");
  });

  it("2. ready to connect", () => {
    expect(
      deriveViewState(
        statusFixture({ connected: false, session_public_id: null, pairing_state: null }),
      ),
    ).toBe("ready-to-connect");
  });

  it("3. creating session", () => {
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          pairing_state: "unpaired",
          session_state: "registered",
          provider_status: null,
        }),
      ),
    ).toBe("creating-session");
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          pairing_state: "pairing_requested",
          session_state: "initializing",
          provider_status: "STARTING",
        }),
      ),
    ).toBe("creating-session");
  });

  it("4. QR available", () => {
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          pairing_state: "pairing_available",
          qr_available: true,
          provider_status: "SCAN_QR_CODE",
        }),
      ),
    ).toBe("qr-available");
  });

  it("5. QR expired / refresh", () => {
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          pairing_state: "pairing_available",
          qr_available: false,
          provider_status: "FAILED",
        }),
      ),
    ).toBe("qr-expired");
  });

  it("6. STARTING / connecting", () => {
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          pairing_state: "paired",
          qr_available: false,
          provider_status: "STARTING",
          session_state: "initializing",
        }),
      ),
    ).toBe("connecting");
  });

  it("7. WORKING / connected", () => {
    expect(deriveViewState(statusFixture({ connected: true }))).toBe("connected");
  });

  it("8. reconnecting / waiting (reconnect eligible)", () => {
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          pairing_state: "paired",
          session_state: "paused",
          provider_status: "STOPPED",
          can_reconnect: true,
        }),
      ),
    ).toBe("reconnect-available");
  });

  it("9. provider degraded / unavailable", () => {
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          pairing_state: "paired",
          session_state: "degraded",
          provider_status: null,
          can_reconnect: false,
          healthy: false,
        }),
      ),
    ).toBe("provider-unavailable");
  });

  it("9b. current outage outranks stale QR and transition signals", () => {
    for (const stale of [
      { pairing_state: "pairing_available", qr_available: true, provider_status: "SCAN_QR_CODE" },
      { pairing_state: "unpaired", session_state: "registered", provider_status: null },
      { pairing_state: "paired", session_state: "initializing", provider_status: "STARTING" },
      { pairing_state: "paired", session_state: "paused", can_reconnect: true },
    ] as const) {
      expect(
        deriveViewState(
          statusFixture({
            ...stale,
            connected: false,
            healthy: false,
            reconnect_blocked_reason: "provider_unavailable",
            provider_session_missing: false,
          }),
        ),
      ).toBe("provider-unavailable");
    }
  });

  it("10. re-auth required", () => {
    expect(
      deriveViewState(
        statusFixture({ connected: false, requires_reauthentication: true, healthy: false }),
      ),
    ).toBe("reauth-required");
  });

  // --- QR-09-D2: provider reachable, its session gone -----------------------------------------

  it("a missing provider session is never rendered as progress", () => {
    // The durable session record still exists, so every "in progress" branch below would have
    // matched and shown "Starting…" — false progress the operator would wait on forever. It is
    // also not "ready-to-connect": that offers an idempotent connect that cannot create the
    // provider session, which is exactly how `/session/pair` became unreachable (QR-09-D6).
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          requires_reauthentication: false,
          provider_session_missing: true,
          session_state: "registered",
          pairing_state: "unpaired",
          provider_status: null,
          can_reconnect: false,
          healthy: false,
        }),
      ),
    ).toBe("ready-to-pair");
  });

  it("QR-09-D6: the durable session is the boundary between connecting and pairing", () => {
    // Same live observation, no durable session behind it: connect() is genuinely the action that
    // creates one, so this must stay "ready-to-connect".
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          requires_reauthentication: false,
          provider_session_missing: true,
          session_public_id: null,
          session_state: null,
          pairing_state: null,
          provider_status: null,
          can_reconnect: false,
          healthy: false,
        }),
      ),
    ).toBe("ready-to-connect");
  });

  it("QR-09-D8 outranks QR-09-D6: an outage never offers the pairing action", () => {
    // A pairing-capable durable session, but the provider is currently unreachable. The observed
    // outage is exclusive of a SESSION_MISSING observation, so nothing here may claim the provider
    // is reachable-and-empty; the operator must be told the truth instead of being handed an
    // action that cannot succeed.
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          requires_reauthentication: false,
          session_state: "registered",
          pairing_state: "unpaired",
          provider_status: null,
          qr_available: false,
          can_reconnect: false,
          healthy: false,
          reconnect_blocked_reason: "provider_unavailable",
          provider_session_missing: false,
        }),
      ),
    ).toBe("provider-unavailable");
  });

  it("a missing provider session on a previously paired connection asks for a new scan", () => {
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          requires_reauthentication: true,
          provider_session_missing: true,
          pairing_state: "paired",
          healthy: false,
        }),
      ),
    ).toBe("reauth-required");
  });

  it("a missing provider session is not reported as the provider being unreachable", () => {
    // The provider answered. Saying "can't be reached" would send the operator to check an
    // outage that is not happening.
    expect(
      deriveViewState(
        statusFixture({
          connected: false,
          requires_reauthentication: false,
          provider_session_missing: true,
          session_state: "degraded",
          pairing_state: "unpaired",
          provider_status: null,
          can_reconnect: false,
          healthy: false,
        }),
      ),
    ).not.toBe("provider-unavailable");
  });

  it("connected takes priority over every other signal", () => {
    // A connected session must never be shown as anything else, even with stale-looking fields.
    expect(
      deriveViewState(
        statusFixture({
          connected: true,
          requires_reauthentication: false,
          qr_available: true,
          can_reconnect: true,
        }),
      ),
    ).toBe("connected");
  });
});

// --- Rendered states -------------------------------------------------------------------------------

describe("WhatsAppQrConnect", () => {
  it("1. renders the not-configured empty state", async () => {
    statusResponse.current = statusFixture({ configured: false });
    withProviders(<WhatsAppQrConnect />);
    expect(await screen.findByText(/isn't available/i)).toBeInTheDocument();
    expect(screen.getByText(/Not available/i)).toBeInTheDocument();
  });

  it("2. ready-to-connect offers a Connect action and it calls the API", async () => {
    statusResponse.current = statusFixture({
      connected: false,
      session_public_id: null,
      pairing_state: null,
      provider_status: null,
    });
    const connected = statusFixture({
      connected: false,
      session_public_id: "sess-1",
      pairing_state: "unpaired",
      session_state: "registered",
      provider_status: null,
    });
    let called = false;
    postHandlers["/session/connect"] = () => {
      called = true;
      return { data: connected };
    };

    withProviders(<WhatsAppQrConnect />);
    const button = await screen.findByRole("button", { name: /connect whatsapp/i });
    fireEvent.click(button);
    await waitFor(() => expect(called).toBe(true));
  });

  // --- QR-09-D6: the pairing action must be reachable and must stay reachable -----------------

  /** Provider reachable, durable session present, never paired, no provider session behind it. */
  function readyToPairFixture(): WhatsAppQrStatus {
    return statusFixture({
      connected: false,
      session_state: "registered",
      pairing_state: "unpaired",
      provider_status: null,
      provider_session_missing: true,
      qr_available: false,
      can_reconnect: false,
      healthy: false,
      health_detail:
        "WhatsApp is reachable but has no session for this connection yet; start the connection and scan the QR code to link an account.",
    });
  }

  it("3. a durable unpaired session with no provider session offers Pair, never Connect", async () => {
    statusResponse.current = readyToPairFixture();
    let connectCalls = 0;
    let pairCalls = 0;
    postHandlers["/session/connect"] = () => {
      connectCalls += 1;
      return { data: statusResponse.current };
    };
    postHandlers["/session/pair"] = () => {
      pairCalls += 1;
      return {
        data: statusFixture({
          connected: false,
          session_state: "waiting_for_pairing",
          pairing_state: "pairing_available",
          provider_status: "SCAN_QR_CODE",
          provider_session_missing: false,
          qr_available: true,
        }),
      };
    };

    withProviders(<WhatsAppQrConnect />);
    const button = await screen.findByRole("button", { name: /begin pairing/i });
    expect(screen.queryByRole("button", { name: /connect whatsapp/i })).not.toBeInTheDocument();
    // Nothing may fetch a QR before pairing has actually been requested.
    expect(qrRequestCount).toBe(0);

    fireEvent.click(button);

    await waitFor(() => expect(pairCalls).toBe(1));
    expect(connectCalls).toBe(0);
    // Pairing genuinely advanced the lifecycle rather than looping back to the same action.
    expect(await screen.findByAltText(/scan this qr code/i)).toBeInTheDocument();
  });

  it("3b. repeated provider-session-missing polls keep the pairing action reachable", async () => {
    statusResponse.current = readyToPairFixture();
    let connectCalls = 0;
    let pairCalls = 0;
    postHandlers["/session/connect"] = () => {
      connectCalls += 1;
      return { data: statusResponse.current };
    };
    postHandlers["/session/pair"] = () => {
      pairCalls += 1;
      return { data: statusResponse.current };
    };
    const { client } = withProviders(<WhatsAppQrConnect />);

    expect(await screen.findByRole("button", { name: /begin pairing/i })).toBeInTheDocument();

    // The live status poll is what regressed the action to "Connect WhatsApp" in QR-09-D6.
    await client.refetchQueries({ queryKey: whatsAppQrKeys.status });
    await client.refetchQueries({ queryKey: whatsAppQrKeys.status });
    await client.refetchQueries({ queryKey: whatsAppQrKeys.status });

    expect(screen.getByRole("button", { name: /begin pairing/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /connect whatsapp/i })).not.toBeInTheDocument();
    // Polling and re-rendering must never fire an operator action on their own.
    expect(pairCalls).toBe(0);
    expect(connectCalls).toBe(0);
    expect(qrRequestCount).toBe(0);
  });

  it("3c. a failed pairing attempt reports the error without falling back to Connect", async () => {
    statusResponse.current = readyToPairFixture();
    postHandlers["/session/pair"] = () => ({ error: new Error("pairing unavailable") });

    withProviders(<WhatsAppQrConnect />);
    fireEvent.click(await screen.findByRole("button", { name: /begin pairing/i }));

    expect(await screen.findByText(/pairing unavailable/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /begin pairing/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /connect whatsapp/i })).not.toBeInTheDocument();
  });

  it("3d. the pairing action stays named and busy while the request is in flight", async () => {
    statusResponse.current = readyToPairFixture();
    let resolvePair!: (value: MockResponse) => void;
    postHandlers["/session/pair"] = () =>
      new Promise<MockResponse>((resolve) => {
        resolvePair = resolve;
      });

    withProviders(<WhatsAppQrConnect />);
    const button = await screen.findByRole("button", { name: /begin pairing/i });
    fireEvent.click(button);

    await waitFor(() => expect(button).toBeDisabled());
    resolvePair({ data: statusResponse.current });
    await waitFor(() => expect(button).not.toBeDisabled());
    expect(screen.queryByRole("button", { name: /connect whatsapp/i })).not.toBeInTheDocument();
  });

  it("3e. a provider outage on a pairing-capable session hides Begin pairing and recovers", async () => {
    statusResponse.current = statusFixture({
      connected: false,
      session_state: "registered",
      pairing_state: "unpaired",
      provider_status: null,
      qr_available: false,
      can_reconnect: false,
      healthy: false,
      reconnect_blocked_reason: "provider_unavailable",
      provider_session_missing: false,
      health_detail: "WhatsApp is temporarily unavailable. Try again shortly.",
    });
    withProviders(<WhatsAppQrConnect />);

    expect(await screen.findByText(/can't be reached right now/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /begin pairing/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /connect whatsapp/i })).not.toBeInTheDocument();
    expect(screen.queryByAltText(/scan this qr code/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^connecting/i)).not.toBeInTheDocument();
    expect(qrRequestCount).toBe(0);

    // Recovery restores the truthful pairing action, and still fetches no QR.
    statusResponse.current = readyToPairFixture();
    fireEvent.click(screen.getByRole("button", { name: /check again/i }));

    expect(await screen.findByRole("button", { name: /begin pairing/i })).toBeInTheDocument();
    expect(qrRequestCount).toBe(0);
  });

  it("3f. ready-to-pair stays visible but non-operable for a read-only actor", async () => {
    permissions.value = ["channels:read"];
    statusResponse.current = readyToPairFixture();
    withProviders(<WhatsAppQrConnect />);

    expect(await screen.findByText(/ready to pair whatsapp/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /begin pairing/i })).not.toBeInTheDocument();
    expect(
      screen.getByText(/pairing requires the channels:authenticate permission/i),
    ).toBeInTheDocument();
  });

  it("4. qr-available renders a live QR image, not a placeholder", async () => {
    statusResponse.current = statusFixture({
      connected: false,
      pairing_state: "pairing_available",
      qr_available: true,
      provider_status: "SCAN_QR_CODE",
    });
    withProviders(<WhatsAppQrConnect />);
    const img = await screen.findByAltText(/scan this qr code/i);
    await waitFor(() => expect(img.getAttribute("src")).toMatch(/^blob:/));
  });

  it("4b. provider outage mounts no QR or pairing action and recovers truthfully", async () => {
    statusResponse.current = statusFixture({
      connected: false,
      pairing_state: "pairing_available",
      session_state: "waiting_for_pairing",
      qr_available: true,
      provider_status: "SCAN_QR_CODE",
      healthy: false,
      reconnect_blocked_reason: "provider_unavailable",
      provider_session_missing: false,
      health_detail: "WhatsApp is temporarily unavailable. Try again shortly.",
    });

    withProviders(<WhatsAppQrConnect />);

    expect(await screen.findByText(/can't be reached right now/i)).toBeInTheDocument();
    expect(screen.queryByAltText(/scan this qr code/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /begin pairing/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /connect whatsapp/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/^connecting/i)).not.toBeInTheDocument();
    expect(qrRequestCount).toBe(0);

    statusResponse.current = statusFixture({
      connected: false,
      pairing_state: "pairing_available",
      session_state: "waiting_for_pairing",
      qr_available: true,
      provider_status: "SCAN_QR_CODE",
      healthy: false,
      reconnect_blocked_reason: "requires_reauth",
      provider_session_missing: false,
    });
    fireEvent.click(screen.getByRole("button", { name: /check again/i }));

    const image = await screen.findByAltText(/scan this qr code/i);
    await waitFor(() => expect(image.getAttribute("src")).toMatch(/^blob:/));
    expect(qrRequestCount).toBe(1);
  });

  it("5. qr-expired offers a retry that requests a fresh pairing attempt", async () => {
    statusResponse.current = statusFixture({
      connected: false,
      pairing_state: "pairing_available",
      qr_available: false,
      provider_status: "FAILED",
    });
    let called = false;
    postHandlers["/session/pair"] = () => {
      called = true;
      return { data: statusResponse.current };
    };
    withProviders(<WhatsAppQrConnect />);
    const button = await screen.findByRole("button", { name: /get a new qr code/i });
    fireEvent.click(button);
    await waitFor(() => expect(called).toBe(true));
  });

  it("7. connected shows the paired identity and a logout action", async () => {
    statusResponse.current = statusFixture();
    withProviders(<WhatsAppQrConnect />);
    expect(await screen.findByText("9193*****553@c.us")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /log out/i })).toBeInTheDocument();
  });

  it("8. reconnect-available offers Reconnect and it calls the API", async () => {
    statusResponse.current = statusFixture({
      connected: false,
      pairing_state: "paired",
      session_state: "paused",
      provider_status: "STOPPED",
      can_reconnect: true,
      healthy: false,
      health_detail: "Session state: paused.",
    });
    let called = false;
    postHandlers["/session/reconnect"] = () => {
      called = true;
      return { data: statusFixture() };
    };
    withProviders(<WhatsAppQrConnect />);
    const button = await screen.findByRole("button", { name: /^reconnect$/i });
    fireEvent.click(button);
    await waitFor(() => expect(called).toBe(true));
  });

  it("10. reauth-required is shown distinctly from a generic error", async () => {
    statusResponse.current = statusFixture({
      connected: false,
      requires_reauthentication: true,
      healthy: false,
      health_detail: "WAHA session requires re-authentication.",
    });
    withProviders(<WhatsAppQrConnect />);
    expect(await screen.findByText(/a new scan is needed/i)).toBeInTheDocument();
  });

  it("11. logout requires explicit confirmation before calling the API", async () => {
    statusResponse.current = statusFixture();
    let called = false;
    postHandlers["/session/logout"] = () => {
      called = true;
      return { data: statusFixture({ connected: false, session_state: "registered", pairing_state: "unpaired" }) };
    };
    withProviders(<WhatsAppQrConnect />);
    fireEvent.click(await screen.findByRole("button", { name: /log out/i }));

    // The dialog must appear and the API must NOT be called until the destructive action is
    // explicitly confirmed inside it.
    const dialog = await screen.findByRole("dialog", { name: /log out of whatsapp/i });
    expect(called).toBe(false);

    fireEvent.click(within(dialog).getByRole("button", { name: /^log out$/i }));
    await waitFor(() => expect(called).toBe(true));
  });

  it("11b. cancelling the logout dialog never calls the API", async () => {
    statusResponse.current = statusFixture();
    let called = false;
    postHandlers["/session/logout"] = () => {
      called = true;
      return { data: statusFixture() };
    };
    withProviders(<WhatsAppQrConnect />);
    fireEvent.click(await screen.findByRole("button", { name: /log out/i }));
    await screen.findByRole("dialog", { name: /log out of whatsapp/i });
    fireEvent.click(screen.getByRole("button", { name: /^cancel$/i }));
    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: /log out of whatsapp/i })).not.toBeInTheDocument(),
    );
    expect(called).toBe(false);
  });

  it("12. permission denied renders without calling the status API at all", async () => {
    permissions.value = [];
    withProviders(<WhatsAppQrConnect />);
    expect(await screen.findByText(/don't have access/i)).toBeInTheDocument();
  });

  it("hides the Connect/Reconnect/Logout actions for a read-only actor", async () => {
    permissions.value = ["channels:read"];
    statusResponse.current = statusFixture({
      connected: false,
      session_public_id: null,
      pairing_state: null,
      provider_status: null,
    });
    withProviders(<WhatsAppQrConnect />);
    await screen.findByText(/connect a whatsapp number/i);
    expect(screen.queryByRole("button", { name: /connect whatsapp/i })).not.toBeInTheDocument();
    expect(screen.getByText(/channels:authenticate permission/i)).toBeInTheDocument();
  });

  it("never renders a QR image outside of qr_available", async () => {
    statusResponse.current = statusFixture({ connected: true });
    withProviders(<WhatsAppQrConnect />);
    await screen.findByText("9193*****553@c.us");
    expect(screen.queryByAltText(/scan this qr code/i)).not.toBeInTheDocument();
  });
});
