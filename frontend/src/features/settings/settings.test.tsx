import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { visibleNavItems } from "@/components/layout/navigation";
import { useQuickReplies as useComposerQuickReplies } from "@/features/inbox/api";
import { ApplicationPanel } from "@/features/settings/ApplicationPanel";
import { CannedMessagesPanel } from "@/features/settings/CannedMessagesPanel";
import { UserAttributesPanel } from "@/features/settings/UserAttributesPanel";
import { FeatureFlagsPanel } from "@/features/settings/FeatureFlagsPanel";
import { KeyValueEditor, type KeyValueEntry } from "@/features/settings/KeyValueEditor";
import { OrganizationPanel } from "@/features/settings/OrganizationPanel";
import { PreferencesPanel } from "@/features/settings/PreferencesPanel";
import {
  useAttributeDefinitions as useCampaignAttributeDefinitions,
  useTags as useCampaignTags,
} from "@/features/campaigns/api";
import {
  useCustomAttributeDefinitions,
  useTags as useContactProfileTags,
} from "@/features/customer-profile/api";
import { SETTINGS_PERMISSIONS, SETTINGS_SECTIONS } from "@/features/settings/sections";
import { TagsPanel } from "@/features/settings/TagsPanel";
import type {
  AttributeDefinition,
  FeatureFlag,
  Organization,
  QuickReply,
  Setting,
  Tag,
} from "@/features/settings/types";
import {
  draftFromValue,
  inferValueType,
  isEditableSetting,
  matchesAttributeFilter,
  parseEnumValues,
  parseValue,
  validateAttributeEnumValues,
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

function tagFixture(overrides: Partial<Tag> = {}): Tag {
  return {
    id: "t1",
    type: "tag",
    name: "Prepaid",
    color: "#1F6FEB",
    description: "Prepaid reactivation cohort.",
    usage_count: 3,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

function quickReplyFixture(overrides: Partial<QuickReply> = {}): QuickReply {
  return {
    id: "qr1",
    shortcut: "hi",
    title: "Greeting",
    body: "Hi there, thanks for reaching out!",
    shared: false,
    usage_count: 0,
    created_at: "2026-07-01T10:00:00Z",
    updated_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

function attributeDefinitionFixture(
  overrides: Partial<AttributeDefinition> = {},
): AttributeDefinition {
  return {
    id: "attr1",
    type: "custom_attribute",
    key_name: "plan",
    label: "Plan",
    data_type: "string",
    enum_values: null,
    is_indexed: false,
    is_pii: false,
    created_at: "2026-07-01T10:00:00Z",
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
/**
 * Per-path write failures, checked before `responses`. Left empty, every existing test's writes
 * behave exactly as before — this only matters to the tests that populate it to simulate a rejected
 * mutation (a duplicate name, a failed delete) without touching backend error semantics.
 */
const writeErrors: Record<string, unknown> = {};

vi.mock("@/lib/api/client", () => {
  const get = async (path: string) =>
    path in responses ? { data: responses[path] } : { error: new Error(`no stub for ${path}`) };
  const write = async (path: string, init?: { body?: unknown }) => {
    writes.push({ path, body: init?.body });
    if (path in writeErrors) return { error: writeErrors[path] };
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
  for (const key of Object.keys(writeErrors)) delete writeErrors[key];
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

// --- Tags -------------------------------------------------------------------------------------

/**
 * The real contact/inbox/customer-profile tag picker, reduced to its data dependency: the same
 * `useTags` hook `Inbox.tsx`, `ContactsList.tsx` and `BulkActionDialog.tsx` import from
 * `customer-profile/api`, under the same `["tags"]` cache key the Settings panel writes through.
 */
function ContactPickerProbe(): JSX.Element {
  const tags = useContactProfileTags();
  return (
    <ul aria-label="Contact tag picker">
      {(tags.data ?? []).map((tag) => (
        <li key={tag.id}>{tag.name}</li>
      ))}
    </ul>
  );
}

/**
 * The real campaign/segment/automation tag picker: the same `useTags` hook `CampaignAudienceStep`,
 * `SegmentEditor` and `AutomationBuilder` import from `campaigns/api`, under the
 * `["campaigns", "pickers", "tags"]` cache key.
 */
function CampaignPickerProbe(): JSX.Element {
  const tags = useCampaignTags();
  return (
    <ul aria-label="Campaign tag picker">
      {(tags.data ?? []).map((tag) => (
        <li key={tag.id}>{tag.name}</li>
      ))}
    </ul>
  );
}

describe("TagsPanel", () => {
  beforeEach(() => {
    permissions.value = ["contacts:read", "contacts:write", "auth:self"];
  });

  it("lists tags with the usage count the read returns", async () => {
    responses["/api/v1/tags"] = [tagFixture()];
    withProviders(<TagsPanel />);

    expect(await screen.findByText("Prepaid")).toBeInTheDocument();
    expect(screen.getByText("3 contacts")).toBeInTheDocument();
    expect(screen.getByText("Prepaid reactivation cohort.")).toBeInTheDocument();
  });

  it("keeps the create action reachable when no tag exists yet", async () => {
    // The gap this panel closes: with no tag and no way to make one, tagging can never start.
    responses["/api/v1/tags"] = [];
    withProviders(<TagsPanel />);

    expect(await screen.findByText("No tags yet")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "New tag" }).length).toBeGreaterThan(0);
  });

  it("creates a tag, sending blank optional fields as null rather than empty strings", async () => {
    responses["/api/v1/tags"] = [];
    withProviders(<TagsPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New tag" }))[0]!);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "  Winback  " } });
    fireEvent.click(screen.getByRole("button", { name: "Create tag" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/tags");
    expect(writes[0]?.body).toEqual({ name: "Winback", color: null, description: null });
  });

  it("refuses a colour the server would reject, before sending it", async () => {
    responses["/api/v1/tags"] = [];
    withProviders(<TagsPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New tag" }))[0]!);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Winback" } });
    fireEvent.change(screen.getByLabelText(/Colour/), { target: { value: "red" } });

    expect(screen.getByText("Use a hex colour such as #1F6FEB")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create tag" })).toBeDisabled();
    expect(writes).toHaveLength(0);
  });

  it("narrows the list by search and by usage", async () => {
    responses["/api/v1/tags"] = [
      tagFixture({ id: "t1", name: "Prepaid", usage_count: 3 }),
      tagFixture({ id: "t2", name: "Postpaid", description: null, usage_count: 0 }),
    ];
    withProviders(<TagsPanel />);

    await screen.findByText("Prepaid");
    fireEvent.change(screen.getByLabelText("Search tags"), { target: { value: "post" } });
    expect(screen.queryByText("Prepaid")).not.toBeInTheDocument();
    expect(screen.getByText("Postpaid")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Search tags"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Filter by usage"), { target: { value: "unused" } });
    expect(screen.queryByText("Prepaid")).not.toBeInTheDocument();
    expect(screen.getByText("Postpaid")).toBeInTheDocument();
  });

  it("edits a tag through the patch endpoint", async () => {
    responses["/api/v1/tags"] = [tagFixture()];
    responses["/api/v1/tags/{tag_id}"] = tagFixture({ name: "Prepaid India" });
    withProviders(<TagsPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Edit Prepaid" }));
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Prepaid India" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/tags/{tag_id}");
    expect(writes[0]?.body).toMatchObject({ name: "Prepaid India" });
  });

  it("says how many contacts a delete would detach before it happens", async () => {
    responses["/api/v1/tags"] = [tagFixture({ usage_count: 3 })];
    // `undefined` stands in for the endpoint's real `204 No Content`: the key is present, so the
    // stub reports success, but there is no body. Treating that as a failure was a live bug.
    responses["/api/v1/tags/{tag_id}"] = undefined;
    withProviders(<TagsPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Delete Prepaid" }));
    expect(screen.getByText(/applied to 3 contacts/)).toBeInTheDocument();
    expect(screen.getByText(/removes the tag from all of them/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete tag" }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/tags/{tag_id}");

    // A successful empty-body delete must close the dialog, not report an error.
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Delete tag" })).not.toBeInTheDocument(),
    );
  });

  it("hides the write controls entirely without contacts:write", async () => {
    permissions.value = ["contacts:read"];
    responses["/api/v1/tags"] = [tagFixture()];
    withProviders(<TagsPanel />);

    await screen.findByText("Prepaid");
    expect(screen.queryByRole("button", { name: "New tag" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit Prepaid" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Prepaid" })).not.toBeInTheDocument();
    expect(screen.getByText(/needs the contacts write permission/)).toBeInTheDocument();
  });

  it("offers a retry when the list fails to load", async () => {
    withProviders(<TagsPanel />);
    expect(await screen.findByRole("button", { name: /Retry/i })).toBeInTheDocument();
  });

  it("shows the loading state before the list resolves", () => {
    // A response is still supplied so the query settles cleanly in the background; the assertion
    // below runs synchronously, before that promise has a chance to resolve.
    responses["/api/v1/tags"] = [tagFixture()];
    withProviders(<TagsPanel />);
    expect(screen.getByText("Loading tags…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("names each row action after its own tag, so a buttons-only list is not all 'Edit'/'Delete'", async () => {
    responses["/api/v1/tags"] = [
      tagFixture({ id: "t1", name: "Prepaid" }),
      tagFixture({ id: "t2", name: "Postpaid" }),
    ];
    withProviders(<TagsPanel />);

    await screen.findByText("Prepaid");
    expect(screen.getByRole("button", { name: "Edit Prepaid" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Prepaid" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Postpaid" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Postpaid" })).toBeInTheDocument();
    // The visible label stays the shared design-system text; only the accessible name is per-row.
    expect(screen.getAllByText("Edit")).toHaveLength(2);
  });

  it("keeps the create dialog open with the typed name intact when it conflicts", async () => {
    responses["/api/v1/tags"] = [tagFixture({ name: "Prepaid" })];
    writeErrors["/api/v1/tags"] = { detail: "A tag named 'Prepaid' already exists." };
    withProviders(<TagsPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New tag" }))[0]!);
    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "Prepaid" } });
    fireEvent.click(screen.getByRole("button", { name: "Create tag" }));

    // The conflict is visible and accessible, not a silently swallowed rejection.
    expect(await screen.findByRole("alert")).toHaveTextContent("A tag named 'Prepaid' already exists.");
    // The dialog is still open — a false success is not shown...
    expect(screen.getByRole("button", { name: "Create tag" })).toBeInTheDocument();
    // ...and the operator's typed value was not thrown away.
    expect(screen.getByLabelText("Name")).toHaveValue("Prepaid");
    expect(writes).toHaveLength(1);
  });

  it("keeps the confirmation open with a visible error when the delete request fails, and allows a retry", async () => {
    responses["/api/v1/tags"] = [tagFixture({ usage_count: 3 })];
    writeErrors["/api/v1/tags/{tag_id}"] = { detail: "This tag could not be deleted right now." };
    withProviders(<TagsPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Delete Prepaid" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete tag" }));

    // The error is visible where the operator is already looking, not hidden behind the dialog.
    expect(await screen.findByRole("alert")).toHaveTextContent("This tag could not be deleted right now.");
    // The confirmation is still open — deletion was not falsely reported as done...
    expect(screen.getByRole("button", { name: "Delete tag" })).toBeInTheDocument();
    // ...and the tag itself is still in the list behind it, because nothing was invalidated.
    expect(screen.getByText("Prepaid")).toBeInTheDocument();

    // Retrying is possible: once the failure clears, the same button succeeds.
    delete writeErrors["/api/v1/tags/{tag_id}"];
    responses["/api/v1/tags/{tag_id}"] = undefined;
    fireEvent.click(screen.getByRole("button", { name: "Delete tag" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Delete tag" })).not.toBeInTheDocument(),
    );
    expect(writes).toHaveLength(2);
  });

  it("does not carry a failed attempt's error into a dialog opened for a different tag", async () => {
    responses["/api/v1/tags"] = [
      tagFixture({ id: "t1", name: "Prepaid" }),
      tagFixture({ id: "t2", name: "Postpaid", description: null, usage_count: 0 }),
    ];
    writeErrors["/api/v1/tags/{tag_id}"] = { detail: "Prepaid could not be saved." };
    withProviders(<TagsPanel />);

    // Fail an edit on Prepaid...
    fireEvent.click(await screen.findByRole("button", { name: "Edit Prepaid" }));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Prepaid could not be saved.");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    // ...then open the editor for a different tag: the earlier failure must not resurface here.
    fireEvent.click(screen.getByRole("button", { name: "Edit Postpaid" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    // The same guarantee applies to the delete-confirmation dialog.
    fireEvent.click(screen.getByRole("button", { name: "Delete Prepaid" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete tag" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Prepaid could not be saved.");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete Postpaid" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("refreshes the existing contact and campaign tag pickers after a create, without a manual reload", async () => {
    responses["/api/v1/tags"] = [tagFixture({ id: "t1", name: "Prepaid" })];

    withProviders(
      <>
        <div data-testid="settings-panel">
          <TagsPanel />
        </div>
        <ContactPickerProbe />
        <CampaignPickerProbe />
      </>,
    );

    // All three real consumers — Settings, the contact/inbox picker and the campaign picker — start
    // from the one shared cache, scoped separately so the shared tag name is not ambiguous.
    const settingsPanel = screen.getByTestId("settings-panel");
    const contactPicker = screen.getByRole("list", { name: "Contact tag picker" });
    const campaignPicker = screen.getByRole("list", { name: "Campaign tag picker" });
    expect(await within(settingsPanel).findByText("Prepaid")).toBeInTheDocument();
    expect(await within(contactPicker).findByText("Prepaid")).toBeInTheDocument();
    expect(await within(campaignPicker).findByText("Prepaid")).toBeInTheDocument();
    expect(within(contactPicker).queryByText("Winback")).not.toBeInTheDocument();
    expect(within(campaignPicker).queryByText("Winback")).not.toBeInTheDocument();

    // The server state a real create leaves behind, so the invalidation-triggered refetches see it.
    responses["/api/v1/tags"] = [
      tagFixture({ id: "t1", name: "Prepaid" }),
      tagFixture({ id: "t2", name: "Winback", usage_count: 0, description: null }),
    ];

    fireEvent.click(within(settingsPanel).getByRole("button", { name: "New tag" }));
    fireEvent.change(within(settingsPanel).getByLabelText("Name"), { target: { value: "Winback" } });
    fireEvent.click(within(settingsPanel).getByRole("button", { name: "Create tag" }));

    // Neither picker is remounted or manually refetched — invalidation alone brings them current.
    await waitFor(() => expect(within(contactPicker).getByText("Winback")).toBeInTheDocument());
    await waitFor(() => expect(within(campaignPicker).getByText("Winback")).toBeInTheDocument());
    expect(within(settingsPanel).getByText("Winback")).toBeInTheDocument();
  });
});

// --- Canned messages ----------------------------------------------------------------------------

/**
 * The real Message Composer picker, reduced to its data dependency: the same `useQuickReplies` hook
 * `MessageComposer.tsx` imports from `inbox/api`, under the identical `["quick-replies"]` cache key
 * the Settings panel writes through.
 */
function ComposerQuickReplyProbe(): JSX.Element {
  const quickReplies = useComposerQuickReplies();
  return (
    <ul aria-label="Composer quick-reply picker">
      {(quickReplies.data ?? []).map((reply) => (
        <li key={reply.id}>{reply.shortcut}</li>
      ))}
    </ul>
  );
}

describe("CannedMessagesPanel", () => {
  beforeEach(() => {
    permissions.value = ["inbox:read", "inbox:write", "auth:self"];
  });

  it("shows the loading state before the list resolves", () => {
    responses["/api/v1/quick-replies"] = { data: [quickReplyFixture()] };
    withProviders(<CannedMessagesPanel />);
    expect(screen.getByText("Loading canned messages…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("keeps the create action reachable when no canned message exists yet", async () => {
    responses["/api/v1/quick-replies"] = { data: [] };
    withProviders(<CannedMessagesPanel />);

    expect(await screen.findByText("No canned messages yet")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "New canned message" }).length).toBeGreaterThan(0);
  });

  it("shows a clean read-only empty state, with no create action, without inbox:write", async () => {
    permissions.value = ["inbox:read"];
    responses["/api/v1/quick-replies"] = { data: [] };
    withProviders(<CannedMessagesPanel />);

    expect(await screen.findByText("No canned messages yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New canned message" })).not.toBeInTheDocument();
    expect(screen.getAllByText(/inbox write permission/).length).toBeGreaterThan(0);
  });

  it("lists replies with a Personal or Shared badge", async () => {
    responses["/api/v1/quick-replies"] = {
      data: [
        quickReplyFixture({ id: "qr1", shortcut: "hi", title: "Greeting", shared: false }),
        quickReplyFixture({ id: "qr2", shortcut: "bye", title: "Sign-off", shared: true }),
      ],
    };
    withProviders(<CannedMessagesPanel />);

    await screen.findByText("Greeting");
    const table = screen.getByRole("table");
    expect(within(table).getByText("Personal")).toBeInTheDocument();
    expect(within(table).getByText("Shared")).toBeInTheDocument();
  });

  it("narrows the list by search across shortcut, title and body", async () => {
    responses["/api/v1/quick-replies"] = {
      data: [
        quickReplyFixture({ id: "qr1", shortcut: "hi", title: "Greeting", body: "Hello there" }),
        quickReplyFixture({ id: "qr2", shortcut: "bye", title: "Sign-off", body: "See you soon" }),
      ],
    };
    withProviders(<CannedMessagesPanel />);

    await screen.findByText("Greeting");
    fireEvent.change(screen.getByLabelText("Search canned messages"), { target: { value: "soon" } });
    expect(screen.queryByText("Greeting")).not.toBeInTheDocument();
    expect(screen.getByText("Sign-off")).toBeInTheDocument();
  });

  it("narrows the list by scope", async () => {
    responses["/api/v1/quick-replies"] = {
      data: [
        quickReplyFixture({ id: "qr1", shortcut: "hi", title: "Greeting", shared: false }),
        quickReplyFixture({ id: "qr2", shortcut: "bye", title: "Sign-off", shared: true }),
      ],
    };
    withProviders(<CannedMessagesPanel />);

    await screen.findByText("Greeting");
    fireEvent.change(screen.getByLabelText("Filter by scope"), { target: { value: "shared" } });
    expect(screen.queryByText("Greeting")).not.toBeInTheDocument();
    expect(screen.getByText("Sign-off")).toBeInTheDocument();
  });

  it("creates a personal reply by default", async () => {
    responses["/api/v1/quick-replies"] = { data: [] };
    withProviders(<CannedMessagesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New canned message" }))[0]!);
    fireEvent.change(screen.getByLabelText("Shortcut"), { target: { value: "hi" } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Greeting" } });
    fireEvent.change(screen.getByLabelText("Body"), { target: { value: "Hi there!" } });
    fireEvent.click(screen.getByRole("button", { name: "Create canned message" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/quick-replies");
    expect(writes[0]?.body).toEqual({ shortcut: "hi", title: "Greeting", body: "Hi there!", shared: false });
  });

  it("creates a shared reply when Shared is selected", async () => {
    responses["/api/v1/quick-replies"] = { data: [] };
    withProviders(<CannedMessagesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New canned message" }))[0]!);
    fireEvent.change(screen.getByLabelText("Shortcut"), { target: { value: "hi" } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Greeting" } });
    fireEvent.change(screen.getByLabelText("Body"), { target: { value: "Hi there!" } });
    fireEvent.change(screen.getByLabelText("Scope"), { target: { value: "shared" } });
    fireEvent.click(screen.getByRole("button", { name: "Create canned message" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toEqual({ shortcut: "hi", title: "Greeting", body: "Hi there!", shared: true });
  });

  it("blocks submission and explains why for an empty shortcut, an over-limit shortcut, title or body", async () => {
    responses["/api/v1/quick-replies"] = { data: [] };
    withProviders(<CannedMessagesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New canned message" }))[0]!);
    const submit = screen.getByRole("button", { name: "Create canned message" });

    // Empty shortcut — the required fields are simply not all filled in yet.
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Greeting" } });
    fireEvent.change(screen.getByLabelText("Body"), { target: { value: "Hi there!" } });
    expect(submit).toBeDisabled();

    // Over-limit shortcut.
    fireEvent.change(screen.getByLabelText("Shortcut"), { target: { value: "x".repeat(61) } });
    expect(screen.getByText("Shortcuts are limited to 60 characters")).toBeInTheDocument();
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Shortcut"), { target: { value: "hi" } });

    // Over-limit title.
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "x".repeat(121) } });
    expect(screen.getByText("Titles are limited to 120 characters")).toBeInTheDocument();
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Greeting" } });

    // Over-limit body.
    fireEvent.change(screen.getByLabelText("Body"), { target: { value: "x".repeat(4097) } });
    expect(screen.getByText("Bodies are limited to 4096 characters")).toBeInTheDocument();
    expect(submit).toBeDisabled();

    expect(writes).toHaveLength(0);
  });

  it("keeps the create dialog open with the typed values intact when the shortcut conflicts", async () => {
    responses["/api/v1/quick-replies"] = { data: [quickReplyFixture({ shortcut: "hi" })] };
    writeErrors["/api/v1/quick-replies"] = {
      detail: "The shortcut 'hi' is already used by a personal quick reply.",
    };
    withProviders(<CannedMessagesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New canned message" }))[0]!);
    fireEvent.change(screen.getByLabelText("Shortcut"), { target: { value: "hi" } });
    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Duplicate" } });
    fireEvent.change(screen.getByLabelText("Body"), { target: { value: "Body text" } });
    fireEvent.click(screen.getByRole("button", { name: "Create canned message" }));

    // The conflict is visible and accessible, not a silently swallowed rejection.
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "The shortcut 'hi' is already used by a personal quick reply.",
    );
    // The dialog is still open — a false success is not shown...
    expect(screen.getByRole("button", { name: "Create canned message" })).toBeInTheDocument();
    // ...and every typed value survives the failed attempt.
    expect(screen.getByLabelText("Shortcut")).toHaveValue("hi");
    expect(screen.getByLabelText("Title")).toHaveValue("Duplicate");
    expect(screen.getByLabelText("Body")).toHaveValue("Body text");
    expect(writes).toHaveLength(1);
  });

  it("edits a reply through the patch endpoint, with scope shown but not editable", async () => {
    responses["/api/v1/quick-replies"] = { data: [quickReplyFixture({ shared: true })] };
    responses["/api/v1/quick-replies/{quick_reply_id}"] = quickReplyFixture({
      shared: true,
      title: "Updated Greeting",
    });
    withProviders(<CannedMessagesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Edit Greeting" }));
    // Scope is informational only — no control can change it once created.
    expect(screen.queryByLabelText("Scope")).not.toBeInTheDocument();
    expect(screen.getByText("Set when a canned message is created and cannot be changed here.")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Title"), { target: { value: "Updated Greeting" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/quick-replies/{quick_reply_id}");
    expect(writes[0]?.body).toEqual({ shortcut: "hi", title: "Updated Greeting", body: quickReplyFixture().body });
  });

  it("deletes through the 204 endpoint", async () => {
    responses["/api/v1/quick-replies"] = { data: [quickReplyFixture()] };
    // `undefined` stands in for the real `204 No Content` — present key, no body.
    responses["/api/v1/quick-replies/{quick_reply_id}"] = undefined;
    withProviders(<CannedMessagesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Delete Greeting" }));
    expect(screen.getByText(/personal canned message, visible only to you/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete canned message" }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/quick-replies/{quick_reply_id}");

    // A successful empty-body delete must close the dialog, not report an error.
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Delete canned message" })).not.toBeInTheDocument(),
    );
  });

  it("keeps the confirmation open with a visible error when the delete fails, and allows a retry", async () => {
    responses["/api/v1/quick-replies"] = { data: [quickReplyFixture()] };
    writeErrors["/api/v1/quick-replies/{quick_reply_id}"] = {
      detail: "This canned message could not be deleted right now.",
    };
    withProviders(<CannedMessagesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Delete Greeting" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete canned message" }));

    // The error is visible where the operator is already looking, not hidden behind the dialog.
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This canned message could not be deleted right now.",
    );
    // The confirmation is still open — deletion was not falsely reported as done...
    expect(screen.getByRole("button", { name: "Delete canned message" })).toBeInTheDocument();
    // ...and the reply itself is still in the list behind it, because nothing was invalidated.
    expect(screen.getByText("Greeting")).toBeInTheDocument();

    // Retrying is possible: once the failure clears, the same button succeeds.
    delete writeErrors["/api/v1/quick-replies/{quick_reply_id}"];
    responses["/api/v1/quick-replies/{quick_reply_id}"] = undefined;
    fireEvent.click(screen.getByRole("button", { name: "Delete canned message" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Delete canned message" })).not.toBeInTheDocument(),
    );
    expect(writes).toHaveLength(2);
  });

  it("does not carry a failed attempt's error into a dialog opened for a different reply", async () => {
    responses["/api/v1/quick-replies"] = {
      data: [
        quickReplyFixture({ id: "qr1", shortcut: "hi", title: "Greeting" }),
        quickReplyFixture({ id: "qr2", shortcut: "bye", title: "Sign-off" }),
      ],
    };
    writeErrors["/api/v1/quick-replies/{quick_reply_id}"] = { detail: "Greeting could not be saved." };
    withProviders(<CannedMessagesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Edit Greeting" }));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Greeting could not be saved.");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: "Edit Sign-off" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete Greeting" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete canned message" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Greeting could not be saved.");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete Sign-off" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("refreshes the real Message Composer picker after a create, without a manual reload", async () => {
    responses["/api/v1/quick-replies"] = { data: [quickReplyFixture({ id: "qr1", shortcut: "hi" })] };

    withProviders(
      <>
        <div data-testid="settings-panel">
          <CannedMessagesPanel />
        </div>
        <ComposerQuickReplyProbe />
      </>,
    );

    const settingsPanel = screen.getByTestId("settings-panel");
    const composerPicker = screen.getByRole("list", { name: "Composer quick-reply picker" });
    expect(await within(settingsPanel).findByText("Greeting")).toBeInTheDocument();
    expect(await within(composerPicker).findByText("hi")).toBeInTheDocument();
    expect(within(composerPicker).queryByText("bye")).not.toBeInTheDocument();

    // The server state a real create leaves behind, so the invalidation-triggered refetch sees it.
    responses["/api/v1/quick-replies"] = {
      data: [
        quickReplyFixture({ id: "qr1", shortcut: "hi" }),
        quickReplyFixture({ id: "qr2", shortcut: "bye", title: "Sign-off" }),
      ],
    };

    fireEvent.click(within(settingsPanel).getByRole("button", { name: "New canned message" }));
    fireEvent.change(within(settingsPanel).getByLabelText("Shortcut"), { target: { value: "bye" } });
    fireEvent.change(within(settingsPanel).getByLabelText("Title"), { target: { value: "Sign-off" } });
    fireEvent.change(within(settingsPanel).getByLabelText("Body"), { target: { value: "See you!" } });
    fireEvent.click(within(settingsPanel).getByRole("button", { name: "Create canned message" }));

    // Not remounted, not manually refetched — invalidation alone brings the composer's picker current.
    await waitFor(() => expect(within(composerPicker).getByText("bye")).toBeInTheDocument());
    expect(within(settingsPanel).getByText("Sign-off")).toBeInTheDocument();
  });

  it("hides every write control without inbox:write, on a populated list", async () => {
    permissions.value = ["inbox:read"];
    responses["/api/v1/quick-replies"] = { data: [quickReplyFixture()] };
    withProviders(<CannedMessagesPanel />);

    await screen.findByText("Greeting");
    expect(screen.queryByRole("button", { name: "New canned message" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit Greeting" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Greeting" })).not.toBeInTheDocument();
    expect(screen.getByText(/inbox write permission/)).toBeInTheDocument();
  });

  it("names each row action after its own canned message", async () => {
    responses["/api/v1/quick-replies"] = {
      data: [
        quickReplyFixture({ id: "qr1", shortcut: "hi", title: "Greeting" }),
        quickReplyFixture({ id: "qr2", shortcut: "bye", title: "Sign-off" }),
      ],
    };
    withProviders(<CannedMessagesPanel />);

    await screen.findByText("Greeting");
    expect(screen.getByRole("button", { name: "Edit Greeting" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Greeting" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit Sign-off" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Sign-off" })).toBeInTheDocument();
    // The visible label stays the shared design-system text; only the accessible name is per-row.
    expect(screen.getAllByText("Edit")).toHaveLength(2);
  });

  it("offers a retry when the list fails to load", async () => {
    withProviders(<CannedMessagesPanel />);
    expect(await screen.findByRole("button", { name: /Retry/i })).toBeInTheDocument();
  });
});

// --- User attributes -----------------------------------------------------------------------------

/**
 * The real Contacts-page picker, reduced to its data dependency: the same `useCustomAttributeDefinitions`
 * hook `ContactsList.tsx` and `BulkActionDialog.tsx` import from `customer-profile/api`, under the
 * identical `["custom-attributes"]` cache key the Settings panel writes through.
 * `ContactsToolbar.tsx` does not read this hook itself — it receives definitions as a prop from
 * `ContactsList.tsx`, so it refreshes transitively through the same list.
 */
function AttributePickerProbe(): JSX.Element {
  const definitions = useCustomAttributeDefinitions();
  return (
    <ul aria-label="Contact attribute picker">
      {(definitions.data ?? []).map((definition) => (
        <li key={definition.id}>{definition.key_name}</li>
      ))}
    </ul>
  );
}

/**
 * The real campaign/segment attribute picker: the same `useAttributeDefinitions` hook
 * `CampaignBasicsStep.tsx`, `SegmentEditor.tsx` and `SegmentDetail.tsx` import from `campaigns/api`,
 * under the `["campaigns", "pickers", "attributes"]` cache key — a prefix of the
 * `["campaigns", "pickers"]` list this panel's mutations invalidate.
 */
function CampaignAttributePickerProbe(): JSX.Element {
  const definitions = useCampaignAttributeDefinitions();
  return (
    <ul aria-label="Campaign attribute picker">
      {(definitions.data ?? []).map((definition) => (
        <li key={definition.id}>{definition.key_name}</li>
      ))}
    </ul>
  );
}

describe("attribute helper functions", () => {
  it("splits, trims and drops empty entries from comma-separated choices", () => {
    expect(parseEnumValues(" gold ,silver,, bronze ")).toEqual(["gold", "silver", "bronze"]);
    expect(parseEnumValues("")).toEqual([]);
    expect(parseEnumValues("   ")).toEqual([]);
  });

  it("requires at least one choice for an enum attribute, and nothing for any other type", () => {
    expect(validateAttributeEnumValues("enum", "")).toMatch(/at least one value/);
    expect(validateAttributeEnumValues("enum", "gold")).toBeNull();
    expect(validateAttributeEnumValues("string", "")).toBeNull();
  });

  it("matches an attribute by key name, label and the exact type filter", () => {
    const plan = attributeDefinitionFixture({ key_name: "plan", label: "Plan", data_type: "enum" });
    const ltv = attributeDefinitionFixture({ key_name: "ltv", label: "LTV", data_type: "number" });

    expect(matchesAttributeFilter(plan, "plan", "all")).toBe(true);
    expect(matchesAttributeFilter(plan, "LTV", "all")).toBe(false);
    expect(matchesAttributeFilter(plan, "", "number")).toBe(false);
    expect(matchesAttributeFilter(ltv, "", "number")).toBe(true);
  });
});

describe("UserAttributesPanel", () => {
  beforeEach(() => {
    permissions.value = ["contacts:read", "contacts:write", "auth:self"];
  });

  it("shows the loading state before the list resolves", () => {
    responses["/api/v1/custom-attributes"] = [attributeDefinitionFixture()];
    withProviders(<UserAttributesPanel />);
    expect(screen.getByText("Loading user attributes…")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("keeps the create action reachable when no attribute exists yet", async () => {
    responses["/api/v1/custom-attributes"] = [];
    withProviders(<UserAttributesPanel />);

    expect(await screen.findByText("No user attributes yet")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "New attribute" }).length).toBeGreaterThan(0);
  });

  it("shows a clean read-only empty state, with no create action, without contacts:write", async () => {
    permissions.value = ["contacts:read"];
    responses["/api/v1/custom-attributes"] = [];
    withProviders(<UserAttributesPanel />);

    expect(await screen.findByText("No user attributes yet")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New attribute" })).not.toBeInTheDocument();
    expect(screen.getAllByText(/contacts write permission/).length).toBeGreaterThan(0);
  });

  it("lists attributes with their type, indexed and PII state", async () => {
    responses["/api/v1/custom-attributes"] = [
      attributeDefinitionFixture({ id: "a1", key_name: "plan", label: "Plan", data_type: "enum", is_indexed: true }),
      attributeDefinitionFixture({ id: "a2", key_name: "notes", label: "Notes", data_type: "string", is_pii: true }),
    ];
    withProviders(<UserAttributesPanel />);

    await screen.findByText("Plan");
    const tbody = screen.getByRole("table").querySelector("tbody")!;
    expect(within(tbody).getByText("Choice list")).toBeInTheDocument();
    expect(within(tbody).getByText("Indexed")).toBeInTheDocument();
    expect(within(tbody).getByText("PII")).toBeInTheDocument();
  });

  it("narrows the list by search across key name and label", async () => {
    responses["/api/v1/custom-attributes"] = [
      attributeDefinitionFixture({ id: "a1", key_name: "plan", label: "Plan" }),
      attributeDefinitionFixture({ id: "a2", key_name: "ltv", label: "LTV" }),
    ];
    withProviders(<UserAttributesPanel />);

    await screen.findByText("Plan");
    fireEvent.change(screen.getByLabelText("Search user attributes"), { target: { value: "ltv" } });
    expect(screen.queryByText("Plan")).not.toBeInTheDocument();
    expect(screen.getByText("LTV")).toBeInTheDocument();
  });

  it("narrows the list by data type", async () => {
    responses["/api/v1/custom-attributes"] = [
      attributeDefinitionFixture({ id: "a1", key_name: "plan", label: "Plan", data_type: "string" }),
      attributeDefinitionFixture({ id: "a2", key_name: "ltv", label: "LTV", data_type: "number" }),
    ];
    withProviders(<UserAttributesPanel />);

    await screen.findByText("Plan");
    fireEvent.change(screen.getByLabelText("Filter by type"), { target: { value: "number" } });
    expect(screen.queryByText("Plan")).not.toBeInTheDocument();
    expect(screen.getByText("LTV")).toBeInTheDocument();
  });

  it("explains a filtered-to-nothing list and offers Clear filters", async () => {
    responses["/api/v1/custom-attributes"] = [attributeDefinitionFixture({ key_name: "plan", label: "Plan" })];
    withProviders(<UserAttributesPanel />);

    await screen.findByText("Plan");
    fireEvent.change(screen.getByLabelText("Search user attributes"), { target: { value: "nope" } });
    expect(await screen.findByText("No user attributes match")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(await screen.findByText("Plan")).toBeInTheDocument();
  });

  it("creates a plain string attribute", async () => {
    responses["/api/v1/custom-attributes"] = [];
    withProviders(<UserAttributesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New attribute" }))[0]!);
    fireEvent.change(screen.getByLabelText("Key name"), { target: { value: "region" } });
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Region" } });
    fireEvent.click(screen.getByRole("button", { name: "Create attribute" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/custom-attributes");
    expect(writes[0]?.body).toEqual({
      key_name: "region",
      label: "Region",
      data_type: "string",
      enum_values: null,
      is_indexed: false,
      is_pii: false,
    });
  });

  it("creates an attribute flagged as PII, leaving indexed unset", async () => {
    responses["/api/v1/custom-attributes"] = [];
    withProviders(<UserAttributesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New attribute" }))[0]!);
    fireEvent.change(screen.getByLabelText("Key name"), { target: { value: "ssn" } });
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "SSN" } });
    fireEvent.click(screen.getByLabelText(/Personally identifiable information/));
    fireEvent.click(screen.getByRole("button", { name: "Create attribute" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toEqual({
      key_name: "ssn",
      label: "SSN",
      data_type: "string",
      enum_values: null,
      is_indexed: false,
      is_pii: true,
    });
  });

  it("creates an enum attribute with its choices, and offers no choice field for a non-enum type", async () => {
    responses["/api/v1/custom-attributes"] = [];
    withProviders(<UserAttributesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New attribute" }))[0]!);
    expect(screen.queryByLabelText("Choices")).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Key name"), { target: { value: "plan" } });
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Plan" } });
    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "enum" } });
    expect(screen.getByLabelText("Choices")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Choices"), { target: { value: "gold, silver" } });
    fireEvent.click(screen.getByLabelText(/Indexed/));
    fireEvent.click(screen.getByRole("button", { name: "Create attribute" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.body).toEqual({
      key_name: "plan",
      label: "Plan",
      data_type: "enum",
      enum_values: ["gold", "silver"],
      is_indexed: true,
      is_pii: false,
    });
  });

  it("blocks submission for an empty or over-limit key name, an over-limit label, and an enum with no choices", async () => {
    responses["/api/v1/custom-attributes"] = [];
    withProviders(<UserAttributesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New attribute" }))[0]!);
    const submit = screen.getByRole("button", { name: "Create attribute" });

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Region" } });
    expect(submit).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Key name"), { target: { value: "x".repeat(61) } });
    expect(screen.getByText("Key names are limited to 60 characters")).toBeInTheDocument();
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Key name"), { target: { value: "region" } });

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "x".repeat(121) } });
    expect(screen.getByText("Labels are limited to 120 characters")).toBeInTheDocument();
    expect(submit).toBeDisabled();
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Region" } });

    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "enum" } });
    expect(submit).toBeDisabled();

    // Punctuation-only input parses to zero choices, surfacing the validator's own message rather
    // than the field's static description (which is present whether or not there is an error).
    fireEvent.change(screen.getByLabelText("Choices"), { target: { value: ",," } });
    expect(screen.getByText("Enum attributes require at least one value")).toBeInTheDocument();
    expect(submit).toBeDisabled();

    expect(writes).toHaveLength(0);
  });

  it("keeps the create dialog open with the typed values intact when the key name conflicts", async () => {
    responses["/api/v1/custom-attributes"] = [attributeDefinitionFixture({ key_name: "plan" })];
    writeErrors["/api/v1/custom-attributes"] = {
      detail: "An attribute named 'plan' already exists.",
    };
    withProviders(<UserAttributesPanel />);

    fireEvent.click((await screen.findAllByRole("button", { name: "New attribute" }))[0]!);
    fireEvent.change(screen.getByLabelText("Key name"), { target: { value: "plan" } });
    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Duplicate" } });
    fireEvent.click(screen.getByRole("button", { name: "Create attribute" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "An attribute named 'plan' already exists.",
    );
    expect(screen.getByRole("button", { name: "Create attribute" })).toBeInTheDocument();
    expect(screen.getByLabelText("Key name")).toHaveValue("plan");
    expect(screen.getByLabelText("Label")).toHaveValue("Duplicate");
    expect(writes).toHaveLength(1);
  });

  it("edits label and flags through the patch endpoint, with key name and type shown but not editable", async () => {
    responses["/api/v1/custom-attributes"] = [
      attributeDefinitionFixture({ key_name: "plan", label: "Plan", data_type: "string" }),
    ];
    responses["/api/v1/custom-attributes/{attribute_id}"] = attributeDefinitionFixture({
      label: "Plan Tier",
    });
    withProviders(<UserAttributesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Edit Plan" }));
    const dialog = screen.getByRole("dialog");
    // Immutable facts are shown as information, not as editable controls.
    expect(screen.queryByLabelText("Key name")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Type")).not.toBeInTheDocument();
    expect(within(dialog).getByText("plan")).toBeInTheDocument();
    expect(within(dialog).getByText("Text")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Label"), { target: { value: "Plan Tier" } });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));

    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/custom-attributes/{attribute_id}");
    expect(writes[0]?.body).toEqual({
      label: "Plan Tier",
      enum_values: null,
      is_indexed: false,
      is_pii: false,
    });
  });

  it("deletes through the 204 endpoint and states that stored values are removed too", async () => {
    responses["/api/v1/custom-attributes"] = [attributeDefinitionFixture({ label: "Plan" })];
    // `undefined` stands in for the real `204 No Content` — present key, no body.
    responses["/api/v1/custom-attributes/{attribute_id}"] = undefined;
    withProviders(<UserAttributesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Delete Plan" }));
    expect(screen.getByText(/removes this attribute and its stored value from every contact/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Delete attribute" }));
    await waitFor(() => expect(writes).toHaveLength(1));
    expect(writes[0]?.path).toBe("/api/v1/custom-attributes/{attribute_id}");

    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Delete attribute" })).not.toBeInTheDocument(),
    );
  });

  it("keeps the confirmation open with a visible error when the delete fails, and allows a retry", async () => {
    responses["/api/v1/custom-attributes"] = [attributeDefinitionFixture({ label: "Plan" })];
    writeErrors["/api/v1/custom-attributes/{attribute_id}"] = {
      detail: "This attribute could not be deleted right now.",
    };
    withProviders(<UserAttributesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Delete Plan" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete attribute" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "This attribute could not be deleted right now.",
    );
    expect(screen.getByRole("button", { name: "Delete attribute" })).toBeInTheDocument();
    // Still in the table behind the dialog, because nothing was invalidated.
    expect(within(screen.getByRole("table")).getByText("Plan")).toBeInTheDocument();

    delete writeErrors["/api/v1/custom-attributes/{attribute_id}"];
    responses["/api/v1/custom-attributes/{attribute_id}"] = undefined;
    fireEvent.click(screen.getByRole("button", { name: "Delete attribute" }));
    await waitFor(() =>
      expect(screen.queryByRole("button", { name: "Delete attribute" })).not.toBeInTheDocument(),
    );
    expect(writes).toHaveLength(2);
  });

  it("does not carry a failed attempt's error into a dialog opened for a different attribute", async () => {
    responses["/api/v1/custom-attributes"] = [
      attributeDefinitionFixture({ id: "a1", key_name: "plan", label: "Plan" }),
      attributeDefinitionFixture({ id: "a2", key_name: "ltv", label: "LTV" }),
    ];
    writeErrors["/api/v1/custom-attributes/{attribute_id}"] = { detail: "Plan could not be saved." };
    withProviders(<UserAttributesPanel />);

    fireEvent.click(await screen.findByRole("button", { name: "Edit Plan" }));
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Plan could not be saved.");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: "Edit LTV" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete Plan" }));
    fireEvent.click(screen.getByRole("button", { name: "Delete attribute" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Plan could not be saved.");
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));

    fireEvent.click(screen.getByRole("button", { name: "Delete LTV" }));
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("refreshes the real Contacts-page and campaign/segment attribute pickers after a create, without a manual reload", async () => {
    responses["/api/v1/custom-attributes"] = [attributeDefinitionFixture({ id: "a1", key_name: "plan", label: "Plan" })];

    withProviders(
      <>
        <div data-testid="settings-panel">
          <UserAttributesPanel />
        </div>
        <AttributePickerProbe />
        <CampaignAttributePickerProbe />
      </>,
    );

    // All three real consumers — Settings, the Contacts-page picker and the campaign/segment
    // picker — start from the one shared `QueryClient`, scoped separately so the shared key name
    // is not ambiguous.
    const settingsPanel = screen.getByTestId("settings-panel");
    const attributePicker = screen.getByRole("list", { name: "Contact attribute picker" });
    const campaignPicker = screen.getByRole("list", { name: "Campaign attribute picker" });
    expect(await within(settingsPanel).findByText("Plan")).toBeInTheDocument();
    expect(await within(attributePicker).findByText("plan")).toBeInTheDocument();
    expect(await within(campaignPicker).findByText("plan")).toBeInTheDocument();
    expect(within(attributePicker).queryByText("region")).not.toBeInTheDocument();
    expect(within(campaignPicker).queryByText("region")).not.toBeInTheDocument();

    responses["/api/v1/custom-attributes"] = [
      attributeDefinitionFixture({ id: "a1", key_name: "plan", label: "Plan" }),
      attributeDefinitionFixture({ id: "a2", key_name: "region", label: "Region", data_type: "string" }),
    ];

    fireEvent.click(within(settingsPanel).getByRole("button", { name: "New attribute" }));
    fireEvent.change(within(settingsPanel).getByLabelText("Key name"), { target: { value: "region" } });
    fireEvent.change(within(settingsPanel).getByLabelText("Label"), { target: { value: "Region" } });
    fireEvent.click(within(settingsPanel).getByRole("button", { name: "Create attribute" }));

    await waitFor(() => expect(within(attributePicker).getByText("region")).toBeInTheDocument());
    await waitFor(() => expect(within(campaignPicker).getByText("region")).toBeInTheDocument());
    expect(within(settingsPanel).getByText("Region")).toBeInTheDocument();
  });

  it("hides every write control without contacts:write, on a populated list", async () => {
    permissions.value = ["contacts:read"];
    responses["/api/v1/custom-attributes"] = [attributeDefinitionFixture({ label: "Plan" })];
    withProviders(<UserAttributesPanel />);

    await screen.findByText("Plan");
    expect(screen.queryByRole("button", { name: "New attribute" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit Plan" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Delete Plan" })).not.toBeInTheDocument();
    expect(screen.getByText(/contacts write permission/)).toBeInTheDocument();
  });

  it("names each row action after its own attribute", async () => {
    responses["/api/v1/custom-attributes"] = [
      attributeDefinitionFixture({ id: "a1", key_name: "plan", label: "Plan" }),
      attributeDefinitionFixture({ id: "a2", key_name: "ltv", label: "LTV" }),
    ];
    withProviders(<UserAttributesPanel />);

    await screen.findByText("Plan");
    expect(screen.getByRole("button", { name: "Edit Plan" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete Plan" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Edit LTV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Delete LTV" })).toBeInTheDocument();
    expect(screen.getAllByText("Edit")).toHaveLength(2);
  });

  it("offers a retry when the list fails to load", async () => {
    withProviders(<UserAttributesPanel />);
    expect(await screen.findByRole("button", { name: /Retry/i })).toBeInTheDocument();
  });
});

// --- Sections & navigation -------------------------------------------------------------------------------------

describe("settings sections", () => {
  it("puts preferences on auth:self so anyone can reach their own record", () => {
    const preferences = SETTINGS_SECTIONS.find((section) => section.key === "preferences");
    expect(preferences?.permission).toBe("auth:self");
  });

  it("puts tags on the contact permission their own endpoints enforce", () => {
    const tags = SETTINGS_SECTIONS.find((section) => section.key === "tags");
    expect(tags?.permission).toBe("contacts:read");
  });

  it("puts canned messages on the inbox permission their own endpoints enforce", () => {
    const cannedMessages = SETTINGS_SECTIONS.find((section) => section.key === "canned-messages");
    expect(cannedMessages?.permission).toBe("inbox:read");
  });

  it("puts user attributes on the contact permission their own endpoints enforce", () => {
    const userAttributes = SETTINGS_SECTIONS.find((section) => section.key === "user-attributes");
    expect(userAttributes?.permission).toBe("contacts:read");
  });

  it("collects the distinct permissions that grant access to the area", () => {
    expect(SETTINGS_PERMISSIONS).toEqual([
      "settings:read",
      "contacts:read",
      "inbox:read",
      "auth:self",
    ]);
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
