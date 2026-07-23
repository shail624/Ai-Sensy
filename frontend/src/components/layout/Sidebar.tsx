import { NavLink } from "react-router-dom";

import { useAuth } from "@/lib/auth";

import { groupedNavItems } from "./navigation";

interface SidebarProps {
  collapsed: boolean;
  className?: string;
  /** Called after a nav item is chosen — used to close the mobile drawer. */
  onNavigate?: () => void;
}

export function Sidebar({ collapsed, className, onNavigate }: SidebarProps): JSX.Element {
  const { hasPermission } = useAuth();
  // Destinations the signed-in user is entitled to reach (Doc 12 RBAC), grouped for scanability.
  const groups = groupedNavItems(hasPermission);

  return (
    <nav
      aria-label="Primary"
      className={`flex-col border-r border-border bg-surface ${collapsed ? "w-[4.5rem]" : "w-64"} ${className ?? ""}`}
    >
      <div className="flex h-16 items-center gap-3 px-4">
        <span
          aria-hidden
          className="brand-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-base font-bold text-white shadow-sm"
        >
          W
        </span>
        {!collapsed ? (
          <span className="flex min-w-0 flex-col leading-tight">
            <span className="truncate text-sm font-semibold text-text-primary">WA Platform</span>
            <span className="truncate text-[11px] text-text-secondary">Business Messaging</span>
          </span>
        ) : null}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-3 pb-4">
        {groups.map((group) => (
          <div key={group.group}>
            {!collapsed ? (
              <p className="px-2 pb-1.5 pt-1 text-[11px] font-semibold uppercase tracking-wider text-text-disabled">
                {group.group}
              </p>
            ) : (
              <div className="mx-2 mb-1.5 mt-1 h-px bg-border" aria-hidden />
            )}
            <ul className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      end={item.path === "/"}
                      onClick={onNavigate}
                      title={collapsed ? item.label : undefined}
                      className={({ isActive }) =>
                        `group relative flex items-center gap-3 rounded-lg px-2.5 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
                          collapsed ? "justify-center" : ""
                        } ${
                          isActive
                            ? "bg-accent-soft text-accent"
                            : "text-text-secondary hover:bg-hover hover:text-text-primary"
                        }`
                      }
                    >
                      {({ isActive }) => (
                        <>
                          {isActive ? (
                            <span
                              aria-hidden
                              className="absolute inset-y-1.5 left-0 w-1 rounded-r-full bg-accent"
                            />
                          ) : null}
                          <Icon
                            aria-hidden
                            className={`h-[18px] w-[18px] shrink-0 ${
                              isActive ? "text-accent" : "text-text-disabled group-hover:text-text-primary"
                            }`}
                          />
                          {!collapsed ? <span className="flex-1 truncate">{item.label}</span> : null}
                        </>
                      )}
                    </NavLink>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
      </div>
    </nav>
  );
}
