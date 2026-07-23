import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AuthProvider, useAuth } from "@/lib/auth";
import {
  clearTokens,
  getAccessToken,
  getRefreshToken,
  hasPersistedSession,
  setTokens,
} from "@/lib/auth/tokens";
import { LoginPage } from "@/pages/LoginPage";
import { RequireAnonymous, RequireAuth, RequirePermission } from "@/routes/guards";

const ME = {
  id: "u1",
  email: "priya@vi.co",
  full_name: "Priya Sharma",
  is_superuser: false,
  roles: ["agent"],
  permissions: ["tasks:read"],
  timezone: "UTC",
  locale: "en",
  mfa_enabled: false,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** Records every outgoing request so header/refresh behaviour can be asserted. */
interface Call {
  url: string;
  authorization: string | null;
}

let calls: Call[] = [];

/**
 * Intercept the transport. openapi-fetch hands `fetch` a fully-built `Request`; it is used as-is
 * (reconstructing it would mix AbortSignal realms between jsdom and Node).
 */
function installFetch(handler: (url: string, request: Request) => Response | Promise<Response>): void {
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const request =
      typeof input === "object" && input !== null && "url" in input && "headers" in input
        ? (input as Request)
        : new Request(new URL(String(input), "http://localhost").toString(), init);
    calls.push({ url: request.url, authorization: request.headers.get("Authorization") });
    return handler(request.url, request);
  });
}

/** Every key/value actually persisted — a stubbed Storage does not serialise via JSON.stringify. */
function storageDump(): string {
  const entries: string[] = [];
  for (let i = 0; i < localStorage.length; i += 1) {
    const key = localStorage.key(i);
    if (key) entries.push(`${key}=${localStorage.getItem(key)}`);
  }
  return entries.join("&");
}

beforeEach(() => {
  calls = [];
  clearTokens();
  localStorage.clear();
});

afterEach(() => {
  vi.unstubAllGlobals();
  clearTokens();
});

describe("token store", () => {
  it("keeps the access token out of persistent storage", () => {
    setTokens("access-1", "refresh-1");

    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
    // The access token must never be findable in localStorage (XSS blast radius).
    const dump = storageDump();
    expect(dump).not.toContain("access-1");
    expect(dump).toContain("refresh-1");
  });

  it("clears both tokens on sign-out", () => {
    setTokens("a", "r");
    clearTokens();
    expect(getAccessToken()).toBeNull();
    expect(getRefreshToken()).toBeNull();
    expect(hasPersistedSession()).toBe(false);
  });
});

function Probe(): JSX.Element {
  const { status, user } = useAuth();
  return (
    <div>
      <span data-testid="status">{status}</span>
      <span data-testid="user">{user?.full_name ?? "-"}</span>
    </div>
  );
}

function renderWithAuth(ui: React.ReactElement, path = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("session bootstrap", () => {
  it("settles anonymous with no persisted refresh token", async () => {
    installFetch(() => jsonResponse({}, 401));
    renderWithAuth(<Probe />);

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    // Nothing was requested — there was no session to restore.
    expect(calls).toHaveLength(0);
  });

  it("restores a session from a persisted refresh token", async () => {
    localStorage.setItem("wa.auth.refresh", "refresh-1");
    installFetch((url) => {
      if (url.includes("/auth/refresh")) {
        return jsonResponse({
          access_token: "access-2",
          token_type: "bearer",
          expires_in: 900,
          refresh_token: "refresh-2",
          user: { id: "u1", email: ME.email, full_name: ME.full_name },
        });
      }
      if (url.includes("/auth/me")) return jsonResponse(ME);
      return jsonResponse({}, 404);
    });

    renderWithAuth(<Probe />);

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("authenticated"));
    expect(screen.getByTestId("user")).toHaveTextContent("Priya Sharma");
    // The rotated refresh token replaced the old one.
    expect(getRefreshToken()).toBe("refresh-2");
    // /auth/me carried the freshly minted access token.
    expect(calls.find((call) => call.url.includes("/auth/me"))?.authorization).toBe(
      "Bearer access-2",
    );
  });

  it("ends the session when the refresh token is rejected", async () => {
    localStorage.setItem("wa.auth.refresh", "expired");
    installFetch(() => jsonResponse({ detail: "expired" }, 401));

    renderWithAuth(<Probe />);

    await waitFor(() => expect(screen.getByTestId("status")).toHaveTextContent("anonymous"));
    expect(getRefreshToken()).toBeNull();
  });
});

describe("401 handling", () => {
  it("refreshes once and replays the failed request", async () => {
    setTokens("stale", "refresh-1");
    let taskCalls = 0;
    installFetch((url) => {
      if (url.includes("/auth/refresh")) {
        return jsonResponse({
          access_token: "fresh",
          token_type: "bearer",
          expires_in: 900,
          refresh_token: "refresh-2",
          user: { id: "u1", email: ME.email, full_name: ME.full_name },
        });
      }
      if (url.includes("/tasks/stats")) {
        taskCalls += 1;
        return taskCalls === 1
          ? jsonResponse({ detail: "expired" }, 401)
          : jsonResponse({ overdue: 1, due_today: 0, upcoming: 0, completed_today: 0 });
      }
      return jsonResponse({}, 404);
    });

    const { api } = await import("@/lib/api/client");
    const result = await api.GET("/api/v1/tasks/stats", { params: { query: {} } });

    expect(result.data?.overdue).toBe(1);
    expect(taskCalls).toBe(2); // original + replay
    const statsCalls = calls.filter((call) => call.url.includes("/tasks/stats"));
    expect(statsCalls[0]?.authorization).toBe("Bearer stale");
    expect(statsCalls[1]?.authorization).toBe("Bearer fresh"); // replayed with the new token
  });

  it("does not attach a bearer token to the login request", async () => {
    setTokens("access-1", "refresh-1");
    installFetch(() => jsonResponse({ detail: "bad credentials" }, 401));

    const { authClient } = await import("@/lib/api/client");
    await authClient.POST("/api/v1/auth/login", {
      body: { email: "a@b.co", password: "x", mfa_code: null },
    });

    expect(calls[0]?.authorization).toBeNull();
  });
});

describe("route guards", () => {
  function Guarded(): JSX.Element {
    return (
      <Routes>
        <Route element={<RequireAnonymous />}>
          <Route path="/login" element={<LoginPage />} />
        </Route>
        <Route element={<RequireAuth />}>
          <Route path="/" element={<span>dashboard</span>} />
          <Route
            path="/tasks"
            element={<RequirePermission code="tasks:read" />}
          >
            <Route index element={<span>tasks module</span>} />
          </Route>
          <Route
            path="/analytics"
            element={<RequirePermission code="analytics:read" />}
          >
            <Route index element={<span>analytics module</span>} />
          </Route>
        </Route>
      </Routes>
    );
  }

  it("redirects an anonymous visitor to the login page", async () => {
    installFetch(() => jsonResponse({}, 401));
    renderWithAuth(<Guarded />, "/");

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Sign in" })).toBeInTheDocument(),
    );
  });

  it("allows an entitled route and blocks an unentitled one", async () => {
    localStorage.setItem("wa.auth.refresh", "refresh-1");
    installFetch((url) => {
      if (url.includes("/auth/refresh")) {
        return jsonResponse({
          access_token: "access-2",
          token_type: "bearer",
          expires_in: 900,
          refresh_token: "refresh-2",
          user: { id: "u1", email: ME.email, full_name: ME.full_name },
        });
      }
      if (url.includes("/auth/me")) return jsonResponse(ME);
      return jsonResponse({}, 404);
    });

    const { unmount } = renderWithAuth(<Guarded />, "/tasks");
    await waitFor(() => expect(screen.getByText("tasks module")).toBeInTheDocument());
    unmount();

    // Same user, a module they hold no permission for.
    renderWithAuth(<Guarded />, "/analytics");
    await waitFor(() =>
      expect(screen.getByText("You don't have access to this area")).toBeInTheDocument(),
    );
    expect(screen.queryByText("analytics module")).not.toBeInTheDocument();
  });
});

describe("LoginPage", () => {
  it("signs in and stores the issued tokens", async () => {
    installFetch((url) => {
      if (url.includes("/auth/login")) {
        return jsonResponse({
          access_token: "access-1",
          token_type: "bearer",
          expires_in: 900,
          refresh_token: "refresh-1",
          user: { id: "u1", email: ME.email, full_name: ME.full_name },
        });
      }
      if (url.includes("/auth/me")) return jsonResponse(ME);
      return jsonResponse({}, 404);
    });

    renderWithAuth(
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<span>dashboard</span>} />
      </Routes>,
      "/login",
    );

    await waitFor(() => expect(screen.getByLabelText("Email")).toBeInTheDocument());
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "priya@vi.co" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "correct-horse" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(screen.getByText("dashboard")).toBeInTheDocument());
    expect(getAccessToken()).toBe("access-1");
    expect(getRefreshToken()).toBe("refresh-1");
  });

  it("surfaces the server's problem detail on bad credentials", async () => {
    installFetch(() => jsonResponse({ detail: "Invalid email or password." }, 401));

    renderWithAuth(<LoginPage />, "/login");

    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "priya@vi.co" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() =>
      expect(screen.getByText("Invalid email or password.")).toBeInTheDocument(),
    );
    expect(getAccessToken()).toBeNull();
  });

  it("validates the form before calling the API", async () => {
    installFetch(() => jsonResponse({}, 500));
    renderWithAuth(<LoginPage />, "/login");

    fireEvent.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(screen.getByText("Email is required")).toBeInTheDocument());
    expect(screen.getByText("Password is required")).toBeInTheDocument();
    expect(calls).toHaveLength(0);
  });
});
