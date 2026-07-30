import { ChevronDown, LayoutGrid, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";

import { primaryNavItems, secondaryNavGroups, type NavItem } from "./navigation";

interface SidebarProps {
  collapsed: boolean;
  className?: string;
  /** Called after a nav item is chosen — used to close the mobile drawer. */
  onNavigate?: () => void;
}

type SecondaryGroup = ReturnType<typeof secondaryNavGroups>[number];

function isCurrentPath(pathname: string, path: string): boolean {
  return path === "/" ? pathname === "/" : pathname === path || pathname.startsWith(`${path}/`);
}

function NavEntry({
  item,
  collapsed,
  onNavigate,
}: {
  item: NavItem;
  collapsed: boolean;
  onNavigate?: () => void;
}): JSX.Element {
  const Icon = item.icon;
  return (
    <li>
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
              <span aria-hidden className="absolute inset-y-1.5 left-0 w-1 rounded-r-full bg-accent" />
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
}

function SecondaryGroupList({
  groups,
  onNavigate,
}: {
  groups: SecondaryGroup[];
  onNavigate?: () => void;
}): JSX.Element {
  return (
    <>
      {groups.map((group) => (
        <div key={group.group} className="mt-3 first:mt-0">
          <p className="px-2 pb-1 text-[10px] font-bold uppercase tracking-[0.12em] text-text-disabled">
            {group.group === "Workspace" ? "More tools" : group.group}
          </p>
          <ul className="space-y-0.5">
            {group.items.map((item) => (
              <NavEntry key={item.path} item={item} collapsed={false} onNavigate={onNavigate} />
            ))}
          </ul>
        </div>
      ))}
    </>
  );
}

export function Sidebar({ collapsed, className, onNavigate }: SidebarProps): JSX.Element {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const primary = primaryNavItems(hasPermission);
  const secondaryGroups = secondaryNavGroups(hasPermission);
  const secondary = secondaryGroups.flatMap((group) => group.items);
  const secondaryActive = secondary.some((item) => isCurrentPath(location.pathname, item.path));
  const [moreOpen, setMoreOpen] = useState(secondaryActive);

  useEffect(() => {
    if (secondaryActive) setMoreOpen(true);
  }, [secondaryActive]);

  const handleSecondaryNavigate = (): void => {
    if (collapsed) setMoreOpen(false);
    onNavigate?.();
  };

  return (
    <nav
      aria-label="Primary"
      className={`relative z-40 flex-col border-r border-border bg-surface transition-[width] duration-200 ${collapsed ? "w-[4.5rem]" : "w-60"} ${className ?? ""}`}
    >
      <div className="flex h-14 items-center gap-2.5 border-b border-border/70 px-3">
        <span
          aria-hidden
          className="brand-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-sm font-bold text-white shadow-sm"
        >
          V
        </span>
        {!collapsed ? (
          <span className="truncate text-sm font-bold tracking-tight text-text-primary">Vi Reactivation</span>
        ) : null}
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-3">
        <ul className="space-y-0.5">
          {primary.map((item) => (
            <NavEntry key={item.path} item={item} collapsed={collapsed} onNavigate={onNavigate} />
          ))}
        </ul>

        {secondary.length > 0 ? (
          collapsed ? (
            <div className="mt-2 border-t border-border/70 pt-2">
              <button
                type="button"
                aria-expanded={moreOpen}
                aria-controls="secondary-navigation"
                title="More tools"
                onClick={() => setMoreOpen((open) => !open)}
                className={`relative flex min-h-10 w-full items-center justify-center rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
                  secondaryActive
                    ? "bg-accent-soft text-accent"
                    : "text-text-secondary hover:bg-hover hover:text-text-primary"
                }`}
              >
                <LayoutGrid aria-hidden className="h-[18px] w-[18px]" />
                <span className="sr-only">More</span>
                {secondaryActive ? (
                  <span aria-hidden className="absolute inset-y-1.5 left-0 w-1 rounded-r-full bg-accent" />
                ) : null}
              </button>
            </div>
          ) : (
            <div className="mt-2 border-t border-border/70 pt-2">
              <button
                type="button"
                aria-expanded={moreOpen}
                aria-controls="secondary-navigation"
                onClick={() => setMoreOpen((open) => !open)}
                className={`flex min-h-10 w-full items-center gap-3 rounded-xl px-2.5 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
                  secondaryActive ? "text-accent" : "text-text-secondary hover:bg-hover hover:text-text-primary"
                }`}
              >
                <LayoutGrid aria-hidden className="h-[18px] w-[18px] shrink-0" />
                <span className="flex-1 text-left">More</span>
                <ChevronDown
                  aria-hidden
                  className={`h-4 w-4 transition-transform ${moreOpen ? "rotate-180" : ""}`}
                />
              </button>

              {moreOpen ? (
                <div id="secondary-navigation" className="mt-1 rounded-xl bg-surface-subtle p-1.5">
                  <SecondaryGroupList groups={secondaryGroups} onNavigate={handleSecondaryNavigate} />
                </div>
              ) : null}
            </div>
          )
        ) : null}
      </div>

      {collapsed && moreOpen && secondary.length > 0 ? (
        <section
          id="secondary-navigation"
          aria-label="More tools"
          className="absolute bottom-3 left-[calc(100%+0.5rem)] top-[4.25rem] z-50 w-72 overflow-y-auto rounded-2xl border border-border bg-surface p-3 shadow-lg"
        >
          <div className="mb-3 flex items-center justify-between gap-3 border-b border-border pb-3">
            <div>
              <h2 className="text-sm font-semibold text-text-primary">More tools</h2>
              <p className="mt-0.5 text-xs text-text-secondary">Advanced workspace and administration</p>
            </div>
            <button
              type="button"
              aria-label="Close more tools"
              onClick={() => setMoreOpen(false)}
              className="flex h-9 w-9 items-center justify-center rounded-xl text-text-secondary hover:bg-hover hover:text-text-primary"
            >
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
          <SecondaryGroupList groups={secondaryGroups} onNavigate={handleSecondaryNavigate} />
        </section>
      ) : null}
    </nav>
  );
}
