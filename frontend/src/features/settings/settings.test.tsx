import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { visibleNavItems } from "@/components/layout/navigation";
import { ApplicationPanel } from "@/features/settings/ApplicationPanel";
import { FeatureFlagsPanel } from "@/features/settings/FeatureFlagsPanel";
import { KeyValueEditor, type KeyValueEntry } from "@/features/settings/KeyValueEditor";
import { OrganizationPanel } from "@/features/settings/OrganizationPanel";
import { PreferencesPanel } from "@/features/settings/PreferencesPanel";
import { SETTINGS_PERMISSIONS, SETTINGS_SECTIONS } from "@/features/settings/sections";
import type { FeatureFlag, Organization, Setting } from "@/features/settings/types";
import {
  draftFromValue,
  inferValueType,
  isEditableSetting,
  parseValue,
  validateKey,
} from "@/features/settings/types";

// --- Fixtures -----------------------------------------------------------------------------------

function orgFixture(overrides: Partial<Organization> = {}): Organization {
  return {
    id: "o1",
    type: "organization",
    name: "Vi Reactivation",
    slug: "vi-reactivation",
    timezone: "Asia/Kolkata",
    default_locale: "en",
    settings: { brand_colour: "#25D366" },
    is_active: true,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    row_version: 4,
    ...overrides,
  };
}

function settingFixture(overrides: Partial<Setting> = {}): Setting {
  return {
    key: "messaging.retry_limit",
    value: 5,
    scope: "organization",
    value_type: "number",
    is_secret: false,
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

function flagFixture(overrides: Partial<FeatureFlag> = {}): FeatureFlag {
  return {
    key: "ai_replies",
    description: "AI-drafted replies in the inbox.",
    is_enabled: false,
    rollout: null,
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

// --- Harness ------------------------------------------------------------------------------------

const permissions = { value: ["settings:read", "settings:manage", "auth:self"] };

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

/** Canned responses per path, so the real hooks and components run without a network. */
const responses: Record<string, unknown> = {};
const writes: { path: string; body: unknown }[] = [];

vi.mock("@/lib/api/client", () => {
  const get = async (path: string) =>
    path in responses ? { data: responses[path] } : { error: new Error(`no stub for ${path}`) };
  const write = async (path: string, init?: { body?: unknown }) => {
    writes.push({ path, body: init?.body });
    return path in responses
      ? { data: responses[path] }
      : { error: new Error("network disabled under test") };
  };
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

beforeEach(() => {
  permissions.value = ["settings:read", "settings:manage", "auth:self"];
  for (const key of Object.keys(responses)) delete responses[key];
  writes.length = 0;
});

// --- Value typing ----------------------------------------------------------------------------------

describe("value typing", () => {
  it("infers the stored type so the editor opens on the right control", () => {
    expect(inferValueType(true)).toBe("boolean");
    expect(inferValueType(42)).toBe("number");
    expect(inferValueType("hello")).toBe("string");
    expect(inferValueType({ a: 1 })).toBe("json");
    expect(inferValueType(null)).toBe("json");
  });

  it("round-trips a value through a draft without changing it", () => {
    for (const value of [true, false, 0, 42, "text", { nested: [1, 2] }] as unknown[]) {
      const parsed = parseValue(draftFromValue(value));
      expect(parsed.ok).toBe(true);
      expect(parsed.value).toEqual(value);
    }
  });

  it("keeps a boolean a boolean rather than the string 'true'", () => {
    // The store is untyped, so `"true"` and `true` are different stored values.
    expect(parseValue({ type: "boolean", text: "true" }).value).toBe(true);
    expect(parseValue({ type: "string", text: "true" }).value).toBe("true");
  });

  it("refuses a number field that is not a number", () => {
    expect(parseValue({ type: "number", text: "" })).toMatchObject({ ok: false });
    expect(parseValue({ type: "number", text: "abc" })).toMatchObject({ ok: false });
    expect(parseValue({ type: "number", text: "3.5" })).toMatchObject({ ok: true, value: 3.5 });
  });

  it("refuses JSON that does not parse rather than storing it as text", () => {
    expect(parseValue({ type: "json", text: "{oops" })).toMatchObject({ ok: false });
    expect(parseValue({ type: "json", text: '{"a":1}' })).toMatchObject({ ok: true });
  });

  it("validates a new key against the store's bounds and its existing keys", () => {
    expect(validateKey("", [])).toMatch(/required/);
    expect(validateKey("x".repeat(121), [])).toMatch(/120 characters/);
    expect(validateKey("taken", ["taken"])).toMatch(/already exists/);
    expect(validateKey("fresh", ["taken"])).toBeNull();
  });
});

describe("setting editability", () => {
  it("treats only non-secret organization settings as writable", () => {
    // `PUT /settings` upserts into the organization scope unconditionally, so a system row cannot
    // be edited through it — writing its key would create a duplicate instead.
    expect(isEditableSetting(settingFixture({ scope: "organization" }))).toBe(true);
    expect(isEditableSetting(settingFixture({ scope: "system" }))).toBe(false);
    expect(isEditableSetting(settingFixture({ is_secret: true }))).toBe(false);
  });
});

// --- KeyValueEditor ---------------------------------------------------------------------------------

describe("KeyValueEditor", () => {
  function entries(overrides: Partial<KeyValueEntry>[] = []): KeyValueEntry[] {
    return overrides.map((entry) => ({
      key: "some.key",
      value: "value",
      editable: true,
      ...entry,
    }));
  }

  function renderEditor(props: Partial<Parameters<typeof KeyValueEditor>[0]> = {}) {
    const onSave = vi.fn();
    withProviders(
      <KeyValueEditor
        entries={entries([{ key: "a.key", value: 1 }])}
        onSave={onSave}
        canEdit
        pending={false}
        error={null}
        emptyTitle="Nothing here"
        emptyDescription="No keys."
        {...props}
      />,
    );
    return onSave;
  }

  it("sends only the keys that were actually changed", () => {
    const onSave = renderEditor({
      entries: entries([
        { key: "a.key", value: 1 },
        { key: "b.key", value: 2 },
      ]),
    });

    fireEvent.change(screen.getByLabelText("Value of a.key"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: /Save 1 change/ }));

    // These APIs upsert, so sending untouched keys would be noise in the audit trail.
    expect(onSave).toHaveBeenCalledWith({ "a.key": 9 });
  });

  it("does not offer a save until something changes", () => {
    renderEditor();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
  });

  it("blocks a save when a value does not parse, and says why", () => {
    const onSave = renderEditor({ entries: entries([{ key: "a.key", value: { x: 1 } }]) });

    fireEvent.change(screen.getByLabelText("Value of a.key"), { target: { value: "{broken" } });
    fireEvent.click(screen.getByRole("button", { name: /Save/ }));

    expect(screen.getByText("Not valid JSON")).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("renders a read-only row without controls, and gives the reason", () => {
    renderEditor({
      entries: entries([
        { key: "sys.key", value: "x", editable: false, readOnlyReason: "Set on the server." },
      ]),
    });
    expect(screen.queryByLabelText("Value of sys.key")).not.toBeInTheDocument();
    expect(screen.getByText("Set on the server.")).toBeInTheDocument();
  });

  it("never renders a secret value, even for an editor", () => {
    renderEditor({
      entries: entries([{ key: "token", value: null, editable: false, secret: true }]),
    });
    expect(screen.getByText(/never returns secret values/)).toBeInTheDocument();
    expect(screen.queryByLabelText("Value of token")).not.toBeInTheDocument();
  });

  it("adds a new key with the type the operator chose", () => {
    const onSave = renderEditor({ allowAdd: true });

    fireEvent.click(screen.getByRole("button", { name: "Add a setting" }));
    fireEvent.change(screen.getByLabelText("New setting key"), {
      target: { value: "feature.enabled" },
    });
    fireEvent.change(screen.getByLabelText("Type of the new setting"), {
      target: { value: "boolean" },
    });
    fireEvent.change(screen.getByLabelText("Value of the new setting"), {
      target: { value: "true" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save/ }));

    expect(onSave).toHaveBeenCalledWith({ "feature.enabled": true });
  });

  it("refuses a duplicate key", () => {
    const onSave = renderEditor({ allowAdd: true, entries: entries([{ key: "taken", value: 1 }]) });

    fireEvent.click(screen.getByRole("button", { name: "Add a setting" }));
    fireEvent.change(screen.getByLabelText("New setting key"), { target: { value: "taken" } });
    fireEvent.click(screen.getByRole("button", { name: /Save/ }));

    expect(screen.getByText("That key already exists")).toBeInTheDocument();
    expect(onSave).not.toHaveBeenCalled();
  });

  it("hides every control from a reader", () => {
    renderEditor({ canEdit: false, allowAdd: true });
    expect(screen.queryByRole("button", { name: /Save/ })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add a setting" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Value of a.key")).not.toBeInTheDocument();
  });
});

// --- Organization -------------------------------------------------------------------------------------

describe("OrganizationPanel", () => {
  it("edits the three fields the update model accepts", async () => {
    responses["/api/v1/organization"] = orgFixture();
    withProviders(<OrganizationPanel />);

    await screen.findByLabelText("Organization name");
    expect(screen.getByLabelText("Timezone")).toHaveValue("Asia/Kolkata");
    expect(screen.getByLabelText("Default locale")).toHaveValue("en");
  });

  it("carries row_version so a concurrent change conflicts instead of overwriting", async () => {
    responses["/api/v1/organization"] = orgFixture({ row_version: 7 });
    withProviders(<OrganizationPanel />);

    fireEvent.change(await screen.findByLabelText("Organization name"), {
      target: { value: "Renamed" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toMatchObject({ name: "Renamed", row_version: 7 });
  });

  it("shows the slug but does not offer it, because the update model has no field for it", async () => {
    responses["/api/v1/organization"] = orgFixture();
    withProviders(<OrganizationPanel />);

    expect(await screen.findByText("vi-reactivation")).toBeInTheDocument();
    expect(screen.queryByLabelText(/slug/i)).not.toBeInTheDocument();
  });

  it("says plainly that no branding or contact fields exist", async () => {
    responses["/api/v1/organization"] = orgFixture();
    withProviders(<OrganizationPanel />);
    expect(
      await screen.findByText(/no logo, brand colours, address or contact details/),
    ).toBeInTheDocument();
  });

  it("merges the free-form settings object rather than replacing it", async () => {
    responses["/api/v1/organization"] = orgFixture({ settings: { a: 1, b: 2 } });
    withProviders(<OrganizationPanel />);

    fireEvent.change(await screen.findByLabelText("Value of a"), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: /Save 1 change/ }));

    await waitFor(() => expect(writes).toHaveLength(1));
    // The PATCH replaces the whole object, so untouched keys must ride along.
    expect(writes[0]?.body).toMatchObject({ settings: { a: 9, b: 2 } });
  });

  it("makes everything read-only without settings:manage", async () => {
    permissions.value = ["settings:read"];
    responses["/api/v1/organization"] = orgFixture();
    withProviders(<OrganizationPanel />);

    expect(await screen.findByLabelText("Organization name")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Save profile" })).not.toBeInTheDocument();
    expect(screen.getByText(/needs settings:manage/)).toBeInTheDocument();
  });

  it("surfaces a load failure with a retry", async () => {
    withProviders(<OrganizationPanel />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

// --- Application settings ------------------------------------------------------------------------------

describe("ApplicationPanel", () => {
  it("separates the two scopes and makes system settings read-only", async () => {
    responses["/api/v1/settings"] = [
      settingFixture({ key: "org.key", scope: "organization" }),
      settingFixture({ key: "sys.key", scope: "system", value: "prod" }),
    ];
    withProviders(<ApplicationPanel />);

    expect(await screen.findByLabelText("Value of org.key")).toBeInTheDocument();
    expect(screen.queryByLabelText("Value of sys.key")).not.toBeInTheDocument();
    expect(screen.getAllByText(/Set on the server/).length).toBeGreaterThan(0);
  });

  it("counts what the store holds, including secrets", async () => {
    responses["/api/v1/settings"] = [
      settingFixture({ key: "a", scope: "organization" }),
      settingFixture({ key: "b", scope: "system" }),
      settingFixture({ key: "c", scope: "organization", is_secret: true, value: null }),
    ];
    withProviders(<ApplicationPanel />);

    const info = await screen.findByText("Settings stored");
    const list = info.closest("dl")!;
    expect(within(list).getByText("3")).toBeInTheDocument();
  });

  it("explains that the store ships empty rather than showing a broken form", async () => {
    responses["/api/v1/settings"] = [];
    withProviders(<ApplicationPanel />);
    expect(await screen.findByText("No organization settings yet")).toBeInTheDocument();
    expect(screen.getByText(/store ships empty/)).toBeInTheDocument();
  });

  it("says retention and messaging defaults are not modelled as settings", async () => {
    responses["/api/v1/settings"] = [];
    withProviders(<ApplicationPanel />);
    expect(await screen.findByText(/not modelled as settings/)).toBeInTheDocument();
  });
});

// --- Feature flags ---------------------------------------------------------------------------------------

describe("FeatureFlagsPanel", () => {
  it("lists flags with their state and description", async () => {
    responses["/api/v1/feature-flags"] = [flagFixture({ is_enabled: true })];
    withProviders(<FeatureFlagsPanel />);

    expect(await screen.findByText("ai_replies")).toBeInTheDocument();
    expect(screen.getByText("Enabled")).toBeInTheDocument();
    expect(screen.getByText("AI-drafted replies in the inbox.")).toBeInTheDocument();
  });

  it("states that flags are global and that nothing reads them yet", async () => {
    responses["/api/v1/feature-flags"] = [flagFixture()];
    withProviders(<FeatureFlagsPanel />);

    expect(await screen.findByText(/global to this deployment/)).toBeInTheDocument();
    expect(screen.getByText(/No module reads them yet/)).toBeInTheDocument();
    expect(screen.getByText("Global")).toBeInTheDocument();
  });

  it("toggles a flag through the patch endpoint", async () => {
    responses["/api/v1/feature-flags"] = [flagFixture({ is_enabled: false })];
    withProviders(<FeatureFlagsPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Enable" }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toEqual({ is_enabled: true });
  });

  it("shows targeting JSON as received, with no editor for it", async () => {
    responses["/api/v1/feature-flags"] = [flagFixture({ rollout: { percentage: 25 } })];
    withProviders(<FeatureFlagsPanel />);

    expect(await screen.findByText(/"percentage": 25/)).toBeInTheDocument();
    expect(screen.getByText(/no editor for them/)).toBeInTheDocument();
  });

  it("is read-only without settings:manage", async () => {
    permissions.value = ["settings:read"];
    responses["/api/v1/feature-flags"] = [flagFixture()];
    withProviders(<FeatureFlagsPanel />);

    await screen.findByText("ai_replies");
    expect(screen.queryByRole("button", { name: "Enable" })).not.toBeInTheDocument();
    expect(screen.getByText("Read-only")).toBeInTheDocument();
  });

  it("explains an empty flag table rather than showing nothing", async () => {
    responses["/api/v1/feature-flags"] = [];
    withProviders(<FeatureFlagsPanel />);
    expect(await screen.findByText("No feature flags")).toBeInTheDocument();
  });
});

// --- Preferences -------------------------------------------------------------------------------------------

describe("PreferencesPanel", () => {
  it("edits the user's own store", async () => {
    responses["/api/v1/users/me/preferences"] = { preferences: { density: "compact" } };
    withProviders(<PreferencesPanel />);

    fireEvent.change(await screen.findByLabelText("Value of density"), {
      target: { value: "comfortable" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Save 1 change/ }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toEqual({ preferences: { density: "comfortable" } });
  });

  it("says where the theme actually lives, so its absence is not a surprise", async () => {
    responses["/api/v1/users/me/preferences"] = { preferences: {} };
    withProviders(<PreferencesPanel />);
    expect(await screen.findByText(/kept in this browser instead/)).toBeInTheDocument();
  });
});

// --- Sections & navigation -------------------------------------------------------------------------------------

describe("settings sections", () => {
  it("puts preferences on auth:self so anyone can reach their own record", () => {
    const preferences = SETTINGS_SECTIONS.find((section) => section.key === "preferences");
    expect(preferences?.permission).toBe("auth:self");
  });

  it("collects the distinct permissions that grant access to the area", () => {
    expect(SETTINGS_PERMISSIONS).toEqual(["settings:read", "auth:self"]);
  });
});

describe("navigation — settings entry", () => {
  it("is visible to someone holding only auth:self", () => {
    expect(visibleNavItems((code) => code === "auth:self").map((item) => item.path)).toContain(
      "/settings",
    );
  });

  it("is visible to a settings reader", () => {
    expect(visibleNavItems((code) => code === "settings:read").map((item) => item.path)).toContain(
      "/settings",
    );
  });

  it("no longer marks any destination as coming soon", () => {
    // Every module in the navigation is now built.
    expect(visibleNavItems(() => true).filter((item) => !item.available)).toEqual([]);
  });
});
