import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";
import { useWorkspacePreferences } from "@/lib/workspace";

import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { navItems, primaryNavItems } from "./navigation";

const COLLAPSE_KEY = "wa.sidebar.compact.v2";

/** New workspaces open on the task rail; an explicit user choice always wins afterwards. */
export function resolveCollapsedPreference(stored: string | null): boolean {
  return stored === null ? true : stored === "1";
}

function readCollapsed(): boolean {
  if (typeof localStorage === "undefined") return true;
  return resolveCollapsedPreference(localStorage.getItem(COLLAPSE_KEY));
}

/**
 * The persistent application shell every module renders inside: a sidebar (collapsible on desktop,
 * a drawer on mobile), the top navigation, and the routed page in `<Outlet />`.
 */
export function AppLayout(): JSX.Element {
  const location = useLocation();
  const { user, hasPermission } = useAuth();
  const workspace = useWorkspacePreferences(user?.id);
  const { recordRecent } = workspace;
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  // Escape closes the mobile drawer (focus returns to the page behind it).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") setMobileOpen(false);
      if (
        event.key === "[" &&
        !(event.target instanceof HTMLInputElement) &&
        !(event.target instanceof HTMLTextAreaElement)
      ) {
        setCollapsed((value) => !value);
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    const path = location.pathname;
    const item = navItems
      .filter((candidate) => candidate.path === "/" ? path === "/" : path.startsWith(candidate.path))
      .sort((a, b) => b.path.length - a.path.length)[0];
    if (item) recordRecent({ label: item.label, path: `${path}${location.search}` });

    requestAnimationFrame(() => {
      const heading = document.querySelector<HTMLElement>("main h1");
      if (!heading) return;
      heading.tabIndex = -1;
      heading.focus({ preventScroll: true });
    });
    // `recordRecent` is stable per signed-in user; pathname/search are the intended triggers.
  }, [location.pathname, location.search, recordRecent]);

  const mobileItems = primaryNavItems(hasPermission).filter((item) =>
    ["/", "/inbox", "/campaigns", "/contacts"].includes(item.path),
  );

  return (
    <div className="flex h-screen overflow-hidden bg-canvas text-text-primary">
      <a
        href="#main-content"
        className="fixed left-3 top-3 z-[100] -translate-y-20 rounded-lg bg-accent px-4 py-2 text-sm font-medium text-accent-fg focus:translate-y-0"
      >
        Skip to content
      </a>
      <Sidebar collapsed={collapsed} className="hidden lg:flex" />

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            onClick={() => setMobileOpen(false)}
            className="absolute inset-0 bg-black/40"
          />
          <Sidebar
            collapsed={false}
            onNavigate={() => setMobileOpen(false)}
            className="absolute inset-y-0 left-0 flex shadow-lg"
          />
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopNav
          collapsed={collapsed}
          onOpenMobileNav={() => setMobileOpen(true)}
          onToggleCollapse={() => setCollapsed((value) => !value)}
        />
        <main id="main-content" className="relative flex-1 overflow-auto pb-16 lg:pb-0">
          <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[radial-gradient(circle_at_top_right,color-mix(in_srgb,var(--color-accent)_8%,transparent),transparent_62%)]" />
          <Outlet />
        </main>
        <nav aria-label="Mobile primary" className="fixed inset-x-0 bottom-0 z-30 flex h-16 items-center justify-around border-t border-border bg-[color-mix(in_srgb,var(--color-bg-surface)_94%,transparent)] px-2 backdrop-blur-xl lg:hidden">
          {mobileItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) => `flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-medium ${isActive ? "bg-accent-soft text-accent" : "text-text-secondary"}`}
              >
                <Icon aria-hidden className="h-[18px] w-[18px]" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
          <button type="button" onClick={() => setMobileOpen(true)} className="flex min-w-14 flex-col items-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-medium text-text-secondary">
            <span aria-hidden className="text-lg leading-[18px]">•••</span>
            <span>More</span>
          </button>
        </nav>
      </div>
    </div>
  );
}
