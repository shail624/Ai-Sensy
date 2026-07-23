import { useState } from "react";
import { Bell, Menu, Moon, PanelLeftClose, PanelLeftOpen, Search, Sun } from "lucide-react";

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

const iconBtn =
  "flex h-9 w-9 items-center justify-center rounded-lg text-text-secondary hover:bg-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

export function TopNav({ collapsed, onOpenMobileNav, onToggleCollapse }: TopNavProps): JSX.Element {
  const { resolvedTheme, toggle } = useTheme();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="flex h-16 shrink-0 items-center gap-2 border-b border-border bg-surface/90 px-3 backdrop-blur sm:px-5">
      <button type="button" aria-label="Open navigation" onClick={onOpenMobileNav} className={`${iconBtn} lg:hidden`}>
        <Menu aria-hidden className="h-[18px] w-[18px]" />
      </button>
      <button
        type="button"
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
        onClick={onToggleCollapse}
        className={`hidden lg:flex ${iconBtn}`}
      >
        {collapsed ? (
          <PanelLeftOpen aria-hidden className="h-[18px] w-[18px]" />
        ) : (
          <PanelLeftClose aria-hidden className="h-[18px] w-[18px]" />
        )}
      </button>

      <h1 className="truncate text-sm font-semibold text-text-primary">WhatsApp Business Platform</h1>

      <div className="ml-auto flex items-center gap-1.5">
        <label className="sr-only" htmlFor="global-search">
          Search
        </label>
        <div className="relative hidden md:block">
          <Search
            aria-hidden
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-disabled"
          />
          <input
            id="global-search"
            type="search"
            disabled
            placeholder="Search…"
            className="w-56 rounded-lg border border-border bg-surface-2 py-2 pl-9 pr-3 text-sm text-text-secondary placeholder:text-text-disabled focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          />
        </div>
        <button type="button" aria-label="Notifications" className={`relative ${iconBtn}`}>
          <Bell aria-hidden className="h-[18px] w-[18px]" />
          <span aria-hidden className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-danger ring-2 ring-surface" />
        </button>
        <button type="button" aria-label="Toggle color theme" onClick={toggle} className={iconBtn}>
          {resolvedTheme === "dark" ? (
            <Sun aria-hidden className="h-[18px] w-[18px]" />
          ) : (
            <Moon aria-hidden className="h-[18px] w-[18px]" />
          )}
        </button>
        <div className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden />
        <div className="relative">
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            aria-label="Account menu"
            onClick={() => setMenuOpen((open) => !open)}
            className="flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
          >
            <span
              aria-hidden
              className="flex h-8 w-8 items-center justify-center rounded-full bg-accent text-xs font-semibold text-accent-fg"
            >
              {user ? initials(user.full_name) : "U"}
            </span>
            {user ? (
              <span className="hidden max-w-[9rem] truncate text-sm font-medium text-text-primary sm:block">
                {user.full_name}
              </span>
            ) : null}
          </button>
          {menuOpen ? (
            <div
              role="menu"
              className="absolute right-0 z-20 mt-2 w-60 overflow-hidden rounded-xl border border-border bg-surface py-1 text-sm shadow-lg"
            >
              {user ? (
                <div className="border-b border-border px-3 py-3">
                  <p className="truncate font-semibold text-text-primary">{user.full_name}</p>
                  <p className="truncate text-xs text-text-secondary">{user.email}</p>
                  {user.roles.length > 0 ? (
                    <p className="mt-1.5 inline-flex rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-medium text-accent">
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
                className="block w-full px-3 py-2 text-left text-text-primary hover:bg-hover"
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
