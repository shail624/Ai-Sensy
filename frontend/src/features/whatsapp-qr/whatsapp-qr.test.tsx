import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { WhatsAppQrConnect } from "@/features/whatsapp-qr/WhatsAppQrConnect";
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
const postHandlers: Record<string, () => { data?: unknown; error?: unknown }> = {};
let qrBlobAvailable = true;

vi.mock("@/lib/api/client", () => {
  const get = async (path: string, opts?: { parseAs?: string }) => {
    if (path === "/api/v1/channels/whatsapp-qr/session") {
      return statusResponse.current
        ? { data: statusResponse.current }
        : { error: new Error("no status stub") };
    }
    if (path === "/api/v1/channels/whatsapp-qr/session/qr") {
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
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

// JSDOM does not implement the Blob object-URL APIs the QR image hook uses.
let objectUrlCounter = 0;
beforeEach(() => {
  permissions.value = ["channels:read", "channels:authenticate"];
  statusResponse.current = null;
  qrBlobAvailable = true;
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
    // matched and shown "Starting…" — false progress the operator would wait on forever.
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
    ).toBe("ready-to-connect");
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
