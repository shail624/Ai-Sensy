import { Star } from "lucide-react";
import { NavLink } from "react-router-dom";

import { useAuth } from "@/lib/auth";
import { useWorkspacePreferences } from "@/lib/workspace";

import { groupedNavItems, visibleNavItems } from "./navigation";

interface SidebarProps {
  collapsed: boolean;
  className?: string;
  /** Called after a nav item is chosen — used to close the mobile drawer. */
  onNavigate?: () => void;
}

export function Sidebar({ collapsed, className, onNavigate }: SidebarProps): JSX.Element {
  const { hasPermission, user } = useAuth();
  const workspace = useWorkspacePreferences(user?.id);
  // Destinations the signed-in user is entitled to reach (Doc 12 RBAC), grouped for scanability.
  const groups = groupedNavItems(hasPermission);
  const visible = visibleNavItems(hasPermission);
  const favoriteItems = visible.filter((item) => workspace.favorites.includes(item.path));

  return (
    <nav
      aria-label="Primary"
      className={`flex-col border-r border-border bg-[color-mix(in_srgb,var(--color-bg-surface)_96%,var(--color-accent-soft))] transition-[width] duration-200 ${collapsed ? "w-[4.75rem]" : "w-[17rem]"} ${className ?? ""}`}
    >
      <div className="flex h-16 items-center gap-3 border-b border-border/70 px-4">
        <span
          aria-hidden
          className="brand-gradient flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] text-base font-bold text-white shadow-md"
        >
          V
        </span>
        {!collapsed ? (
          <span className="flex min-w-0 flex-col leading-tight">
            <span className="truncate text-sm font-bold tracking-tight text-text-primary">Vi Reactivation</span>
            <span className="truncate text-[11px] text-text-secondary">Customer engagement suite</span>
          </span>
        ) : null}
      </div>

      <div className="flex-1 space-y-5 overflow-y-auto px-3 py-4">
        {favoriteItems.length > 0 ? (
          <div>
            {!collapsed ? <p className="flex items-center gap-1.5 px-2 pb-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-text-disabled"><Star aria-hidden className="h-3 w-3" /> Favorites</p> : <div className="mx-2 mb-1.5 h-px bg-border" aria-hidden />}
            <ul className="space-y-0.5">
              {favoriteItems.map((item) => {
                const Icon = item.icon;
                return <li key={`favorite-${item.path}`}><NavLink to={item.path} end={item.path === "/"} onClick={onNavigate} title={collapsed ? item.label : undefined} className={({isActive}) => `group flex min-h-10 items-center gap-3 rounded-xl px-2.5 text-sm font-medium transition-colors ${collapsed ? "justify-center" : ""} ${isActive ? "bg-accent-soft text-accent" : "text-text-secondary hover:bg-hover hover:text-text-primary"}`}><Icon aria-hidden className="h-[18px] w-[18px] shrink-0" />{!collapsed ? <span className="truncate">{item.label}</span> : null}</NavLink></li>;
              })}
            </ul>
          </div>
        ) : null}
        {groups.map((group) => (
          <div key={group.group}>
            {!collapsed ? (
              <p className="px-2 pb-1.5 pt-1 text-[10px] font-bold uppercase tracking-[0.14em] text-text-disabled">
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
                        `group relative flex min-h-10 items-center gap-3 rounded-xl px-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
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

      {!collapsed ? (
        <div className="m-3 rounded-xl border border-border bg-surface px-3 py-2.5">
          <div className="flex items-center gap-2">
            <span aria-hidden className="h-2 w-2 rounded-full bg-success shadow-[0_0_0_3px_var(--color-success-soft)]" />
            <span className="text-xs font-medium text-text-primary">RC1 release baseline</span>
          </div>
          <p className="mt-1 text-[10px] leading-relaxed text-text-disabled">Official Meta Cloud API · RC1 baseline</p>
        </div>
      ) : null}
    </nav>
  );
}
