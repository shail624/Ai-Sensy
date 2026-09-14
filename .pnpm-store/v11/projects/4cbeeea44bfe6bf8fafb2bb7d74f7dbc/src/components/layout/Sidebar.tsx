import { ChevronDown, Settings, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";

import { useAuth } from "@/lib/auth";

import { manageNavGroups, primaryNavItems, type NavItem } from "./navigation";

interface SidebarProps {
  collapsed: boolean;
  className?: string;
  onNavigate?: () => void;
  onClose?: () => void;
}

const GROUP_LABELS: Record<string, string> = {
  Workspace: "Vi & audience tools",
  Tools: "Workspace tools",
  Platform: "Platform controls",
};

function matchesPath(pathname: string, path: string): boolean {
  const base = path.split("#")[0]!;
  return base === "/" ? pathname === "/" : pathname === base || pathname.startsWith(`${base}/`);
}

export function Sidebar({ collapsed, className, onNavigate, onClose }: SidebarProps): JSX.Element {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const primary = primaryNavItems(hasPermission);
  const groups = manageNavGroups(hasPermission);
  const secondary = groups.flatMap((group) => group.items);
  // Prefer the most specific destination, and match hash entry points independently.
  const activeSecondary = secondary
    .filter((item) => matchesPath(location.pathname, item.path)
      && (!item.path.includes("#") || item.path.endsWith(location.hash) && Boolean(location.hash)))
    .sort((a, b) => b.path.length - a.path.length)[0]?.path;
  const [moreOpen, setMoreOpen] = useState(Boolean(activeSecondary));
  const manageRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  const panelId = onClose ? "mobile-manage-navigation" : "manage-navigation";

  useEffect(() => {
    setMoreOpen(Boolean(activeSecondary));
  }, [location.pathname, location.hash, activeSecondary]);

  function closeManage(): void {
    setMoreOpen(false);
    manageRef.current?.focus();
  }

  function renderEntry(item: NavItem, panel = false): JSX.Element {
    const Icon = item.icon;
    const compact = collapsed && !panel;
    const caption = compact ? item.railLabel ?? item.label : item.label;
    return (
      <li key={item.path}>
        <NavLink
          to={item.path}
          end={item.path === "/"}
          onClick={onNavigate}
          aria-label={compact && item.railLabel ? `${caption} — ${item.label}` : undefined}
          aria-current={panel ? activeSecondary === item.path ? "page" : false : undefined}
          title={compact ? `${item.label}${item.maturity ? ` (${item.maturity})` : ""}` : undefined}
          className={({ isActive }) => {
            const active = panel ? activeSecondary === item.path : isActive;
            return `group relative flex items-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus ${
              compact ? "min-h-[68px] flex-col justify-center gap-1 px-1 py-2 text-center text-[11px] font-medium leading-tight"
                : "min-h-11 gap-3 rounded-md px-3 py-2 text-sm font-medium"
            } ${panel
              ? active ? "bg-accent-soft text-accent" : "text-text-primary hover:bg-hover"
              : active ? "bg-[var(--color-nav-active-bg)] text-[var(--color-nav-text)]" : "text-[var(--color-nav-muted)] hover:bg-[var(--color-nav-hover)] hover:text-[var(--color-nav-text)]"}`;
          }}
        >
          {({ isActive }) => <>
            {(panel ? activeSecondary === item.path : isActive) && !panel ? (
              <span aria-hidden className="absolute inset-y-2 left-0 w-0.5 bg-[var(--color-nav-indicator)]" />
            ) : null}
            <Icon aria-hidden className={`${compact ? "h-6 w-6" : "h-[18px] w-[18px]"} shrink-0`} />
            <span className={compact ? "max-w-full break-words" : "min-w-0 flex-1"}>{caption}</span>
            {item.maturity ? (
              <span className={`${compact ? "text-[8px]" : "rounded px-1 text-[9px]"} uppercase tracking-wide opacity-80`}>{item.maturity}</span>
            ) : null}
          </>}
        </NavLink>
      </li>
    );
  }

  const manageContents = groups.map((group) => (
    <div key={group.group} className="mt-5 first:mt-0">
      {group.group !== "Manage" ? (
        <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-text-secondary">
          {GROUP_LABELS[group.group] ?? group.group}
        </p>
      ) : null}
      <ul className="space-y-1">{group.items.map((item) => renderEntry(item, true))}</ul>
    </div>
  ));

  return (
    <div className={`shrink-0 ${className ?? "flex"}`}>
      <nav
        aria-label="Primary"
        className={`flex min-h-0 flex-col border-r border-[var(--color-nav-border)] bg-[var(--color-nav-bg)] ${collapsed ? "w-[84px]" : "w-64 max-w-[85vw]"}`}
      >
        <div className={`flex h-14 shrink-0 items-center gap-2.5 border-b border-[var(--color-nav-border)] px-3 ${collapsed ? "justify-center" : ""}`}>
          <span aria-hidden className="brand-gradient flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-xs font-extrabold text-white">VR</span>
          {!collapsed ? <span className="min-w-0 flex-1 text-sm font-bold text-[var(--color-nav-text)]">Vi Reactivation</span> : null}
          {onClose ? (
            <button type="button" aria-label="Close navigation" onClick={onClose} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-[var(--color-nav-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
              <X aria-hidden className="h-5 w-5" />
            </button>
          ) : null}
        </div>

        <div className={`min-h-0 flex-1 overflow-y-auto py-2 ${collapsed ? "" : "px-2"}`}>
          <ul>{primary.map((item) => renderEntry(item))}</ul>
          {secondary.length > 0 ? (
            <button
              ref={manageRef}
              type="button"
              aria-expanded={moreOpen}
              aria-controls={panelId}
              onClick={() => setMoreOpen((value) => !value)}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight" && moreOpen && collapsed) {
                  event.preventDefault();
                  panelRef.current?.querySelector<HTMLElement>("a")?.focus();
                }
              }}
              className={`flex w-full items-center font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus ${collapsed ? "min-h-[68px] flex-col justify-center gap-1 text-[11px]" : "min-h-11 gap-3 rounded-md px-3 text-sm"} ${moreOpen || activeSecondary ? "bg-[var(--color-nav-active-bg)] text-[var(--color-nav-text)]" : "text-[var(--color-nav-muted)] hover:bg-[var(--color-nav-hover)]"}`}
            >
              <Settings aria-hidden className={collapsed ? "h-6 w-6" : "h-[18px] w-[18px]"} />
              <span>Manage</span>
              {!collapsed ? <ChevronDown aria-hidden className={`ml-auto h-4 w-4 ${moreOpen ? "rotate-180" : ""}`} /> : null}
            </button>
          ) : null}
          {!collapsed && moreOpen ? (
            <div id={panelId} className="mt-2 rounded-md bg-surface p-2">{manageContents}</div>
          ) : null}
        </div>
      </nav>

      {collapsed && moreOpen && secondary.length > 0 ? (
        <section
          ref={panelRef}
          id={panelId}
          aria-label="Manage"
          onKeyDown={(event) => {
            if (event.key === "Escape") { event.preventDefault(); closeManage(); }
          }}
          className="flex w-64 min-h-0 flex-col border-r border-border bg-surface"
        >
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-5">
            <h2 className="text-lg font-semibold text-text-primary">Manage</h2>
            <button type="button" aria-label="Close manage panel" onClick={closeManage} className="flex h-9 w-9 items-center justify-center rounded-md text-text-secondary hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-3 py-4">{manageContents}</div>
        </section>
      ) : null}
    </div>
  );
}
