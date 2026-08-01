import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";
import { useWorkspacePreferences } from "@/lib/workspace";

import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";
import { navItems, primaryNavItems, secondaryNavGroups } from "./navigation";

const COLLAPSE_KEY = "wa.sidebar.compact.v2";
const FOCUSABLE =
  'a[href], button:not([disabled]):not([tabindex="-1"]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

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
  const mobileDialogRef = useRef<HTMLDivElement>(null);
  const mobileInvokerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
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
    if (!mobileOpen) return;
    const dialog = mobileDialogRef.current;
    requestAnimationFrame(() =>
      dialog?.querySelector<HTMLElement>('nav [aria-label="Close navigation"]')?.focus(),
    );

    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileOpen(false);
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const focusable = [...dialog.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (focusable.length === 0) return;
      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      mobileInvokerRef.current?.focus();
    };
  }, [mobileOpen]);

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
  const mobileItemPaths = new Set(mobileItems.map((item) => item.path));
  const primaryOverflowItems = primaryNavItems(hasPermission).filter(
    (item) => !mobileItemPaths.has(item.path),
  );
  const secondaryItems = secondaryNavGroups(hasPermission).flatMap((group) => group.items);
  const moreItems = [...primaryOverflowItems, ...secondaryItems];
  const secondaryActive = moreItems.some((item) =>
    item.path === "/"
      ? location.pathname === "/"
      : location.pathname === item.path || location.pathname.startsWith(`${item.path}/`),
  );

  const openMobileNavigation = (): void => {
    mobileInvokerRef.current = document.activeElement as HTMLElement | null;
    setMobileOpen(true);
  };

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
        <div
          ref={mobileDialogRef}
          id="mobile-navigation"
          role="dialog"
          aria-modal="true"
          aria-label="Navigation"
          className="fixed inset-0 z-40 lg:hidden"
        >
          <button
            type="button"
            aria-label="Dismiss navigation"
            tabIndex={-1}
            onClick={() => setMobileOpen(false)}
            className="absolute inset-0 bg-black/40"
          />
          <Sidebar
            collapsed={false}
            onNavigate={() => setMobileOpen(false)}
            onClose={() => setMobileOpen(false)}
            className="absolute inset-y-0 left-0 flex shadow-lg"
          />
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <TopNav
          collapsed={collapsed}
          mobileNavOpen={mobileOpen}
          onOpenMobileNav={openMobileNavigation}
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
                className={({ isActive }) => `flex min-h-11 min-w-14 flex-col items-center justify-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${isActive ? "bg-accent-soft text-accent" : "text-text-secondary hover:bg-hover hover:text-text-primary"}`}
              >
                <Icon aria-hidden className="h-[18px] w-[18px]" />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
          {moreItems.length > 0 ? (
            <button
              type="button"
              aria-controls="mobile-navigation"
              aria-expanded={mobileOpen}
              aria-current={secondaryActive ? "page" : undefined}
              onClick={openMobileNavigation}
              className={`flex min-h-11 min-w-14 flex-col items-center justify-center gap-1 rounded-xl px-2 py-1.5 text-[10px] font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${secondaryActive ? "bg-accent-soft text-accent" : "text-text-secondary hover:bg-hover hover:text-text-primary"}`}
            >
              <span aria-hidden className="text-lg leading-[18px]">•••</span>
              <span>More</span>
            </button>
          ) : null}
        </nav>
      </div>
    </div>
  );
}
