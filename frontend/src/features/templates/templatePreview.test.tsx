import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { TemplateDetail } from "@/features/templates/TemplateDetail";
import type { Template, TemplatePreview } from "@/features/templates/types";

/**
 * The preview an operator checks a mass send against.
 *
 * The screen used to render with no sample values at all, so it showed the template — which the
 * template list already showed — rather than a message. These tests are about the difference:
 * whether what an operator types actually reaches the render, and whether a link's destination is
 * visible once it does.
 */

const permissions = { value: ["templates:read"] };
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions: permissions.value, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.value.includes(code),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => vi.fn() };
});

const template = {
  id: "t1",
  type: "template",
  waba_id: "w1",
  name: "vi_reactivation_offer",
  language: "en",
  category: "marketing",
  status: "approved",
  quality_score: "GREEN",
  rejection_reason: null,
  components: [
    { type: "body", text: "Hi {{1}}, your Vi number is due." },
    {
      type: "buttons",
      buttons: [{ type: "url", text: "Recharge now", url: "https://vi.co/pay/{{1}}" }],
    },
  ],
  variable_count: 1,
  has_media_header: false,
  is_sendable: true,
  last_synced_at: null,
  row_version: 1,
  created_at: "2026-09-01T00:00:00Z",
  updated_at: "2026-09-01T00:00:00Z",
} as unknown as Template;

const asked = vi.hoisted(() => ({ calls: [] as unknown[] }));

// Mocked outright rather than partially: importing the real module pulls `@/lib/auth` back in
// through its own permission helper, and the point here is the preview, not the module graph.
vi.mock("@/features/templates/api", () => {
  return {
    apiErrorMessage: (error: unknown) => String(error),
    useHasPermission: () => false,
    useDeleteTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useTemplateVersions: () => ({ data: [], isPending: false, isError: false, error: null }),
    useTemplate: () => ({ data: template, isPending: false, isError: false, error: null }),
    useTemplatePreview: (_id: string, values?: unknown) => {
      asked.calls.push(values);
      const body = (values as { body?: string[] } | undefined)?.body?.[0];
      const link = (values as { buttons?: string[] } | undefined)?.buttons?.[0];
      const preview: TemplatePreview = {
        header: "",
        body: `Hi ${body || "{{1}}"}, your Vi number is due.`,
        footer: "",
        buttons: [
          {
            index: 0,
            type: "url",
            text: "Recharge now",
            target: `https://vi.co/pay/${link || "{{1}}"}`,
            takes_value: true,
          },
        ],
        expects: { header: 0, body: 1, buttons: 1 },
      };
      return {
        data: preview,
        isLoading: false,
        isPending: false,
        isError: false,
        error: null,
        refetch: vi.fn(),
      };
    },
  };
});

function withProviders(node: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{node}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  asked.calls = [];
  permissions.value = ["templates:read"];
});

describe("template preview", () => {
  it("offers one box per variable the server says the template takes", () => {
    withProviders(<TemplateDetail templateId="t1" />);

    expect(screen.getByLabelText("Body value 1")).toBeInTheDocument();
    expect(screen.getByLabelText("Button link value 1")).toBeInTheDocument();
    // No header variables on this template, so no header box.
    expect(screen.queryByLabelText("Header value 1")).not.toBeInTheDocument();
  });

  it("sends what an operator types through to the render", async () => {
    withProviders(<TemplateDetail templateId="t1" />);

    fireEvent.change(screen.getByLabelText("Body value 1"), { target: { value: "Priya" } });

    await waitFor(() =>
      expect(screen.getByText("Hi Priya, your Vi number is due.")).toBeInTheDocument(),
    );
  });

  it("shows where the link actually goes once its value is supplied", async () => {
    // The case that has no other screen: the variable lives inside the URL, so a wrong mapping is
    // invisible until a customer taps it — and by then everyone has the same link.
    withProviders(<TemplateDetail templateId="t1" />);

    fireEvent.change(screen.getByLabelText("Button link value 1"), {
      target: { value: "TXN9931" },
    });

    await waitFor(() =>
      expect(screen.getByText("https://vi.co/pay/TXN9931")).toBeInTheDocument(),
    );
  });

  it("leaves an unsupplied variable visible rather than inventing one", () => {
    withProviders(<TemplateDetail templateId="t1" />);

    expect(screen.getByText("Hi {{1}}, your Vi number is due.")).toBeInTheDocument();
    expect(screen.getByText("https://vi.co/pay/{{1}}")).toBeInTheDocument();
  });

  it("does not send blank boxes as empty values", () => {
    // An empty string would substitute into the link and render a plausible URL that goes
    // somewhere wrong; left out, the placeholder stays and says the mapping is short.
    withProviders(<TemplateDetail templateId="t1" />);

    fireEvent.change(screen.getByLabelText("Body value 1"), { target: { value: "Priya" } });
    fireEvent.change(screen.getByLabelText("Body value 1"), { target: { value: "" } });

    expect(screen.getByText("Hi {{1}}, your Vi number is due.")).toBeInTheDocument();
  });
});
