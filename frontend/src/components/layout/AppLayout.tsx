import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

const COLLAPSE_KEY = "wa.sidebar.collapsed";

function readCollapsed(): boolean {
  return typeof localStorage !== "undefined" && localStorage.getItem(COLLAPSE_KEY) === "1";
}

/**
 * The persistent application shell every module renders inside: a sidebar (collapsible on desktop,
 * a drawer on mobile), the top navigation, and the routed page in `<Outlet />`.
 */
export function AppLayout(): JSX.Element {
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  // Escape closes the mobile drawer (focus returns to the page behind it).
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") setMobileOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-canvas text-text-primary">
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
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
