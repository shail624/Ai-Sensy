import { useState } from "react";

import { useAuth } from "@/lib/auth";
import { useTheme } from "@/lib/theme";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "U";
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (`${first}${last}` || "U").toUpperCase();
}

interface TopNavProps {
  collapsed: boolean;
  onOpenMobileNav: () => void;
  onToggleCollapse: () => void;
}

export function TopNav({ collapsed, onOpenMobileNav, onToggleCollapse }: TopNavProps): JSX.Element {
  const { resolvedTheme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border bg-surface px-3 sm:px-4">
      <button
        type="button"
        aria-label="Open navigation"
        onClick={onOpenMobileNav}
        className="rounded-md p-2 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus lg:hidden"
      >
        <span aria-hidden>☰</span>
      </button>
      <button
        type="button"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        onClick={onToggleCollapse}
        className="hidden rounded-md p-2 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus lg:inline-flex"
      >
        <span aria-hidden>{collapsed ? "»" : "«"}</span>
      </button>

      <h1 className="truncate text-sm font-semibold">WhatsApp Business Platform</h1>

      <div className="ml-auto flex items-center gap-1.5">
        <label className="sr-only" htmlFor="global-search">
          Search
        </label>
        <input
          id="global-search"
          type="search"
          disabled
          placeholder="Search… (coming soon)"
          className="hidden w-48 rounded-md border border-border bg-surface-2 px-2 py-1 text-sm text-text-disabled md:block"
        />
        <button
          type="button"
          aria-label="Notifications (coming soon)"
          className="rounded-md p-2 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          <span aria-hidden>🔔</span>
        </button>
        <button
          type="button"
          aria-label="Toggle color theme"
          onClick={toggle}
          className="rounded-md p-2 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
        >
          <span aria-hidden>{resolvedTheme === "dark" ? "☀" : "☾"}</span>
        </button>
        <div className="relative">
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label="Account menu"
            onClick={() => setMenuOpen((open) => !open)}
            className="flex h-8 w-8 items-center justify-center rounded-full bg-surface-2 text-xs font-medium hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            <span aria-hidden>{user ? initials(user.full_name) : "U"}</span>
          </button>
          {menuOpen ? (
            <div
              role="menu"
              className="absolute right-0 z-10 mt-1 w-56 rounded-md border border-border bg-surface py-1 text-sm shadow-lg"
            >
              {user ? (
                <div className="border-b border-border px-3 py-2">
                  <p className="truncate font-medium text-text-primary">{user.full_name}</p>
                  <p className="truncate text-xs text-text-secondary">{user.email}</p>
                  {user.roles.length > 0 ? (
                    <p className="mt-0.5 truncate text-xs text-text-disabled">
                      {user.roles.join(", ")}
                    </p>
                  ) : null}
                </div>
              ) : null}
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  void logout();
                }}
                className="block w-full px-3 py-1.5 text-left text-text-primary hover:bg-hover"
              >
                Sign out
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
