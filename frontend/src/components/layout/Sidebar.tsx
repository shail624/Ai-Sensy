import { NavLink } from "react-router-dom";

import { useAuth } from "@/lib/auth";

import { visibleNavItems } from "./navigation";

interface SidebarProps {
  collapsed: boolean;
  className?: string;
  /** Called after a nav item is chosen — used to close the mobile drawer. */
  onNavigate?: () => void;
}

export function Sidebar({ collapsed, className, onNavigate }: SidebarProps): JSX.Element {
  const { hasPermission } = useAuth();
  // Destinations the signed-in user is entitled to reach (Doc 12 RBAC).
  const items = visibleNavItems(hasPermission);

  return (
    <nav
      aria-label="Primary"
      className={`flex-col border-r border-border bg-surface ${collapsed ? "w-16" : "w-56"} ${className ?? ""}`}
    >
      <div className="flex h-14 items-center gap-2 border-b border-border px-4">
        <span
          aria-hidden
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-accent text-sm font-bold text-accent-fg"
        >
          W
        </span>
        {!collapsed ? <span className="truncate text-sm font-semibold">WA Platform</span> : null}
      </div>

      <ul className="flex-1 space-y-1 overflow-y-auto p-2">
        {items.map((item) => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              end={item.path === "/"}
              onClick={onNavigate}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-2 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
                  isActive
                    ? "bg-accent text-accent-fg"
                    : "text-text-secondary hover:bg-hover hover:text-text-primary"
                }`
              }
            >
              <span
                aria-hidden
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-xs font-semibold"
              >
                {item.glyph}
              </span>
              {!collapsed ? <span className="flex-1 truncate">{item.label}</span> : null}
              {!collapsed && !item.available ? (
                <span className="rounded bg-surface-2 px-1.5 py-0.5 text-[10px] uppercase text-text-disabled">
                  Soon
                </span>
              ) : null}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
