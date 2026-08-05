import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { Breadcrumbs } from "@/components/layout/Breadcrumbs";
import { AppLayout, resolveCollapsedPreference } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopNav } from "@/components/layout/TopNav";
import { ThemeProvider } from "@/lib/theme";

// The shell reads the session for nav entitlement and the account menu. These specs are about
// layout, so the session is stubbed as a fully entitled user; auth behaviour has its own suite.
const logout = vi.fn();
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: {
      id: "u1",
      email: "priya@vi.co",
      full_name: "Priya Sharma",
      is_superuser: true,
      roles: ["owner"],
      permissions: [],
      timezone: "UTC",
      locale: "en",
      mfa_enabled: false,
    },
    login: vi.fn(),
    logout,
    hasPermission: () => true,
  }),
  useHasPermission: () => true,
}));
import { DashboardPage } from "@/pages/DashboardPage";

// The dashboard hosts the data-backed My Work Queue widget (Doc 14 §11), so the harness supplies a
// query client; retries are off so error paths settle immediately.
function renderAt(ui: React.ReactElement, path = "/") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Sidebar", () => {
  it("keeps everyday destinations visible and places advanced areas under More", () => {
    renderAt(<Sidebar collapsed={false} />);
    for (const label of ["Dashboard", "Live Chat", "Contacts", "Campaigns", "Templates", "Analytics"]) {
      expect(screen.getByRole("link", { name: new RegExp(label, "i") })).toBeInTheDocument();
    }
    expect(screen.queryByRole("link", { name: /media/i })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "More" }));
    expect(screen.getByRole("link", { name: /media/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /settings/i })).toBeInTheDocument();
    expect(screen.getAllByText("foundation")).toHaveLength(1);
    expect(screen.getByText("future")).toBeInTheDocument();
  });

  it("automatically reveals More when an advanced destination is active", () => {
    renderAt(<Sidebar collapsed={false} />, "/media");
    expect(screen.getByRole("button", { name: "More" })).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("link", { name: /media/i })).toHaveAttribute("aria-current", "page");
  });

  it("keeps the compact More panel closed on an advanced destination", () => {
    renderAt(<Sidebar collapsed />, "/automation");
    expect(screen.getByRole("button", { name: "More" })).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("region", { name: "More tools" })).not.toBeInTheDocument();
  });

  it("highlights the active route", () => {
    renderAt(<Sidebar collapsed={false} />, "/contacts");
    expect(screen.getByRole("link", { name: /contacts/i })).toHaveAttribute("aria-current", "page");
    expect(screen.getByRole("link", { name: /dashboard/i })).not.toHaveAttribute("aria-current");
  });

  // The Sidebar still badges an item marked `available: false`; there is simply no such item in
  // `navItems` any more, because every destination in the navigation is now built.
  it("shows no coming-soon badge now that every destination is built", () => {
    renderAt(<Sidebar collapsed={false} />);
    expect(screen.queryByText("Soon")).not.toBeInTheDocument();
  });

  it("hides labels when collapsed but keeps the links reachable", () => {
    renderAt(<Sidebar collapsed />);
    expect(screen.queryByText("Contacts")).not.toBeInTheDocument();
    expect(screen.getByTitle("Contacts")).toBeInTheDocument();
  });

  it("keeps advanced destinations behind one More panel on the compact rail", () => {
    renderAt(<Sidebar collapsed />);
    expect(screen.queryByRole("link", { name: /media/i })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "More" }));
    const panel = screen.getByRole("region", { name: "More tools" });
    expect(within(panel).getByRole("link", { name: /media/i })).toBeInTheDocument();
    expect(within(panel).getByRole("link", { name: /settings/i })).toBeInTheDocument();

    fireEvent.click(within(panel).getByRole("button", { name: "Close more tools" }));
    expect(screen.queryByRole("region", { name: "More tools" })).not.toBeInTheDocument();
  });
});

describe("sidebar preference", () => {
  it("defaults new workspaces to the compact rail and preserves explicit choices", () => {
    expect(resolveCollapsedPreference(null)).toBe(true);
    expect(resolveCollapsedPreference("1")).toBe(true);
    expect(resolveCollapsedPreference("0")).toBe(false);
  });
});

describe("TopNav", () => {
  function renderTopNav() {
    return renderAt(
      <ThemeProvider>
        <TopNav collapsed={false} mobileNavOpen={false} onOpenMobileNav={vi.fn()} onToggleCollapse={vi.fn()} />
      </ThemeProvider>,
    );
  }

  it("shows the application title and placeholders", () => {
    renderTopNav();
    expect(screen.queryByText("WhatsApp Business")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /search/i })).toBeEnabled();
    expect(screen.getByLabelText(/notification center/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/toggle color theme/i)).not.toBeInTheDocument();
  });

  it("opens the account menu", () => {
    renderTopNav();
    const trigger = screen.getByLabelText("Account menu");
    expect(trigger).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(trigger);
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    const menu = screen.getByRole("menu");
    // The name also shows in the top-bar trigger, so scope the assertion to the open menu.
    expect(within(menu).getByText("Priya Sharma")).toBeInTheDocument();
    expect(within(menu).getByRole("menuitem", { name: /switch to dark mode/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("menuitem", { name: "Sign out" }));
    expect(logout).toHaveBeenCalled();
  });

  it("uses the shared modal focus and Escape contract for keyboard shortcuts", () => {
    renderTopNav();
    const account = screen.getByLabelText("Account menu");
    fireEvent.click(account);
    fireEvent.click(screen.getByRole("menuitem", { name: "Keyboard shortcuts" }));

    const dialog = screen.getByRole("dialog", { name: "Keyboard shortcuts" });
    expect(dialog).toHaveFocus();
    expect(document.body.style.overflow).toBe("hidden");
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Keyboard shortcuts" })).not.toBeInTheDocument();
    expect(account).toHaveFocus();
  });

  it("opens the permission-aware command palette with governed create actions", () => {
    renderTopNav();
    const searchButton = screen.getByRole("button", { name: /search/i });
    searchButton.focus();
    fireEvent.click(searchButton);
    const palette = screen.getByRole("dialog", { name: "Search and commands" });
    expect(within(palette).getByRole("button", { name: /Campaign Create Build a governed WhatsApp broadcast/i })).toBeInTheDocument();
    expect(within(palette).getByText(/Future module/)).toBeInTheDocument();
    expect(within(palette).queryByText(/billing|payments|marketplace/i)).not.toBeInTheDocument();
    fireEvent.keyDown(palette, { key: "Escape" });
    expect(screen.queryByRole("dialog", { name: "Search and commands" })).not.toBeInTheDocument();
    expect(searchButton).toHaveFocus();
  });

  it("toggles the sidebar", () => {
    const onToggleCollapse = vi.fn();
    renderAt(
      <ThemeProvider>
        <TopNav collapsed={false} mobileNavOpen={false} onOpenMobileNav={vi.fn()} onToggleCollapse={onToggleCollapse} />
      </ThemeProvider>,
    );
    fireEvent.click(screen.getByLabelText("Collapse sidebar"));
    expect(onToggleCollapse).toHaveBeenCalledOnce();
  });

  it("exposes the mobile navigation state to assistive technology", () => {
    renderAt(
      <ThemeProvider>
        <TopNav collapsed={false} mobileNavOpen onOpenMobileNav={vi.fn()} onToggleCollapse={vi.fn()} />
      </ThemeProvider>,
    );
    const trigger = screen.getByRole("button", { name: "Open navigation" });
    expect(trigger).toHaveAttribute("aria-expanded", "true");
    expect(trigger).toHaveAttribute("aria-controls", "mobile-navigation");
  });
});

describe("AppLayout mobile navigation", () => {
  it("marks More active and closes the labelled navigation drawer explicitly", () => {
    renderAt(
      <ThemeProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="media" element={<h1>Media library</h1>} />
          </Route>
        </Routes>
      </ThemeProvider>,
      "/media",
    );

    const mobileNav = screen.getByRole("navigation", { name: "Mobile primary" });
    const more = within(mobileNav).getByRole("button", { name: "More" });
    expect(more).toHaveAttribute("aria-current", "page");
    fireEvent.click(more);

    const drawer = screen.getByRole("dialog", { name: "Navigation" });
    expect(more).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(within(drawer).getByRole("button", { name: "Close navigation" }));
    expect(screen.queryByRole("dialog", { name: "Navigation" })).not.toBeInTheDocument();
  });

  it("marks More active for primary destinations that overflow the mobile task bar", () => {
    renderAt(
      <ThemeProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="templates" element={<h1>Templates</h1>} />
          </Route>
        </Routes>
      </ThemeProvider>,
      "/templates",
    );

    const mobileNav = screen.getByRole("navigation", { name: "Mobile primary" });
    expect(within(mobileNav).getByRole("button", { name: "More" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("toggles the desktop rail between compact and expanded states", () => {
    localStorage.setItem("wa.sidebar.compact.v2", "1");
    renderAt(
      <ThemeProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<h1>Dashboard</h1>} />
          </Route>
        </Routes>
      </ThemeProvider>,
    );

    fireEvent.click(screen.getByRole("button", { name: "Expand sidebar" }));

    expect(screen.getByRole("button", { name: "Collapse sidebar" })).toBeInTheDocument();
    expect(screen.getByText("Vi Reactivation")).toBeInTheDocument();
  });
});

describe("Breadcrumbs", () => {
  it("links earlier crumbs and marks the last as current", () => {
    renderAt(<Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Inbox" }]} />);
    expect(screen.getByRole("link", { name: "Dashboard" })).toHaveAttribute("href", "/");
    expect(screen.getByText("Inbox")).toHaveAttribute("aria-current", "page");
  });
});

describe("PageHeader", () => {
  it("renders the title and description", () => {
    render(<PageHeader title="Contacts" description="All contacts" />);
    expect(screen.getByRole("heading", { name: "Contacts" })).toBeInTheDocument();
    expect(screen.getByText("All contacts")).toBeInTheDocument();
  });
});

describe("DashboardPage", () => {
  it("keeps primary actions without repeating the navigation catalog", () => {
    const { container } = renderAt(<DashboardPage />);
    expect(screen.getByRole("link", { name: /live chat/i })).toHaveAttribute("href", "/inbox");
    expect(screen.getByRole("link", { name: /new campaign/i })).toHaveAttribute("href", "/campaigns/new");
    expect(container.querySelector('a[href="/settings/whatsapp"]')).not.toBeInTheDocument();
    expect(screen.queryByRole("navigation", { name: "Quick links" })).not.toBeInTheDocument();
    expect(screen.queryByText("Recent")).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Modules" })).not.toBeInTheDocument();
  });

  // The cards exclude Settings, and every other destination is now built, so nothing on the
  // dashboard is a placeholder. The "Coming Soon" badge still renders for a card that is not
  // available — `Sidebar` above covers that path — there is simply no such card here any more.
  it("shows no coming-soon placeholder now that every carded module is built", () => {
    renderAt(<DashboardPage />);
    expect(screen.queryByText("Coming Soon")).not.toBeInTheDocument();
  });
});
