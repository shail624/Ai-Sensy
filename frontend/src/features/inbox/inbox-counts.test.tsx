import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { ConversationFilters } from "@/features/inbox/ConversationFilters";

const permissions = ["inbox:read", "inbox:write", "inbox:assign"];
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.includes(code),
  }),
  useHasPermission: (code: string) => permissions.includes(code),
}));

const counts = { value: undefined as undefined | Record<string, number> };
vi.mock("@/features/inbox/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/inbox/api")>()),
  useAssignableUsers: () => ({ data: [] }),
  useConversationCounts: () => ({ data: counts.value }),
}));

function renderFilters() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ConversationFilters
          filters={{ status: "open" }}
          onChange={vi.fn()}
          tags={[]}
          savedViews={[]}
          onSaveView={vi.fn()}
          onDeleteView={vi.fn()}
          currentUserId="u1"
        />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("inbox category counts", () => {
  it("shows each category's total once the server has answered", () => {
    counts.value = { active: 12, requesting: 5, intervened: 3 };

    renderFilters();

    expect(screen.getByLabelText("12 in Active")).toBeInTheDocument();
    expect(screen.getByLabelText("5 in Requesting")).toBeInTheDocument();
    expect(screen.getByLabelText("3 in Intervened")).toBeInTheDocument();
  });

  it("omits the badge while the count is still loading rather than showing zero", () => {
    // A zero badge during the read would assert an emptiness the inbox has not established —
    // the operator would see "0 Requesting" on a queue that in fact has work waiting.
    counts.value = undefined;

    renderFilters();

    expect(screen.queryByLabelText(/in Active$/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Active/ })).toBeInTheDocument();
  });

  it("renders a real zero once the server reports one", () => {
    counts.value = { active: 0, requesting: 0, intervened: 0 };

    renderFilters();

    // Distinct from the loading case above: an answered zero is a fact worth showing.
    expect(screen.getByLabelText("0 in Requesting")).toBeInTheDocument();
  });
});
