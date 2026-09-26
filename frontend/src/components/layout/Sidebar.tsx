import { ChevronDown, type LucideIcon, Settings, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";

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

/** The AiSensy-style rail entry: a 70×54 cell, 20px icon, 10px caption. */
const RAIL_ITEM =
  "group flex h-[54px] w-full flex-col items-center justify-start pb-1 pt-1.5 text-center text-[var(--color-nav-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus";

function RailContent({ icon: Icon, label, active }: { icon: LucideIcon; label: string; active: boolean }): JSX.Element {
  return (
    <>
      <span
        aria-hidden
        className={`flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full transition-colors duration-500 ${
          active ? "bg-[var(--color-nav-active-bg)] text-[var(--color-nav-active-fg)]" : "group-hover:bg-white/15"
        }`}
      >
        <Icon className="h-5 w-5" />
      </span>
      <span className="mt-0 w-full truncate px-0.5 text-[10px] leading-[14.3px]">{label}</span>
    </>
  );
}

const BOTTOM_PATHS = new Set(["/operations/api"]);

function matchesPath(pathname: string, path: string): boolean {
  const base = path.split("#")[0]!;
  return base === "/" ? pathname === "/" : pathname === base || pathname.startsWith(`${base}/`);
}

export function Sidebar({ collapsed, className, onNavigate, onClose }: SidebarProps): JSX.Element {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  // The reference rail pins developer tooling to its own block at the bottom edge.
  const allPrimary = primaryNavItems(hasPermission);
  const primary = allPrimary.filter((item) => !BOTTOM_PATHS.has(item.path));
  const bottom = allPrimary.filter((item) => BOTTOM_PATHS.has(item.path));
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
            if (compact) return RAIL_ITEM;
            return `group relative flex items-center transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus ${panel ? "h-10 gap-4 rounded-[5px] px-2.5 text-sm font-normal" : "min-h-11 gap-3 rounded-md px-3 py-2 text-sm font-medium"} ${panel
              ? active ? "bg-[#ebf5f3] text-[var(--color-nav-bg)] dark:bg-accent-soft dark:text-accent" : "text-[#141414] hover:bg-black/[0.03] dark:text-text-primary dark:hover:bg-hover"
              : active ? "bg-[var(--color-nav-hover)] text-[var(--color-nav-text)]" : "text-[var(--color-nav-muted)] hover:bg-[var(--color-nav-hover)] hover:text-[var(--color-nav-text)]"}`;
          }}
        >
          {({ isActive }) => compact ? (
            <RailContent icon={Icon} label={caption} active={isActive} />
          ) : <>
            <Icon aria-hidden className={`${panel ? "h-5 w-5" : "h-[18px] w-[18px]"} shrink-0`} />
            <span className="min-w-0 flex-1 truncate">{caption}</span>
            {item.maturity ? (
              <span className="rounded px-1 text-[9px] uppercase tracking-wide">{item.maturity}</span>
            ) : null}
          </>}
        </NavLink>
      </li>
    );
  }

  const manageContents = groups.map((group) => (
    <div key={group.group} className="mt-5 first:mt-0">
      {group.group !== "Manage" ? (
        <p className="mb-1.5 px-2.5 text-[11px] font-medium uppercase tracking-wider text-[#808080]">
          {GROUP_LABELS[group.group] ?? group.group}
        </p>
      ) : null}
      <ul className="space-y-1.5">{group.items.map((item) => renderEntry(item, true))}</ul>
    </div>
  ));

  return (
    <div className={`shrink-0 ${className ?? "flex"}`}>
      <nav
        aria-label="Primary"
        className={`flex min-h-0 flex-col bg-[var(--color-nav-bg)] transition-[width] duration-200 motion-reduce:transition-none ${collapsed ? "w-[70px]" : "w-64 max-w-[85vw]"}`}
      >
        <div className={`flex h-14 shrink-0 items-center gap-2.5 px-3 ${collapsed ? "justify-center px-0" : ""}`}>
          <span aria-hidden className="brand-gradient flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-xs font-extrabold text-white">VR</span>
          {!collapsed ? <span className="min-w-0 flex-1 text-sm font-bold text-[var(--color-nav-text)]">Vi Reactivation</span> : null}
          {onClose ? (
            <button type="button" aria-label="Close navigation" onClick={onClose} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md text-[var(--color-nav-text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
              <X aria-hidden className="h-5 w-5" />
            </button>
          ) : null}
        </div>

        <div className={`min-h-0 flex-1 overflow-y-auto ${collapsed ? "py-0.5 [scrollbar-width:none]" : "px-2 py-2"}`}>
          <ul>{primary.map((item) => renderEntry(item))}</ul>
          {secondary.length > 0 ? (
            <button
              ref={manageRef}
              type="button"
              aria-expanded={moreOpen}
              aria-controls={panelId}
              onClick={() => {
                if (!activeSecondary && collapsed && secondary[0]) {
                  navigate(secondary[0].path);
                  onNavigate?.();
                  setMoreOpen(true);
                  return;
                }
                setMoreOpen((value) => !value);
              }}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight" && moreOpen && collapsed) {
                  event.preventDefault();
                  panelRef.current?.querySelector<HTMLElement>("a")?.focus();
                }
              }}
              className={collapsed ? RAIL_ITEM : `flex w-full min-h-11 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-focus ${moreOpen || activeSecondary ? "bg-[var(--color-nav-hover)] text-[var(--color-nav-text)]" : "text-[var(--color-nav-muted)] hover:bg-[var(--color-nav-hover)]"}`}
            >
              {collapsed ? (
                <RailContent icon={Settings} label="Manage" active={moreOpen || Boolean(activeSecondary)} />
              ) : <>
                <Settings aria-hidden className="h-[18px] w-[18px]" />
                <span>Manage</span>
                <ChevronDown aria-hidden className={`ml-auto h-4 w-4 transition-transform duration-200 ${moreOpen ? "rotate-180" : ""}`} />
              </>}
            </button>
          ) : null}
          {!collapsed && moreOpen ? (
            <div id={panelId} className="mt-2 rounded-md bg-surface p-2">{manageContents}</div>
          ) : null}
        </div>
        {bottom.length > 0 ? (
          <ul className={`shrink-0 pb-2 ${collapsed ? "" : "px-2"}`}>{bottom.map((item) => renderEntry(item))}</ul>
        ) : null}
      </nav>

      {collapsed && moreOpen && secondary.length > 0 ? (
        <section
          ref={panelRef}
          id={panelId}
          aria-label="Manage"
          onKeyDown={(event) => {
            if (event.key === "Escape") { event.preventDefault(); closeManage(); }
          }}
          className="flex w-[261px] min-h-0 flex-col border-r border-[#f0f0f0] bg-surface dark:border-border"
        >
          <div className="flex shrink-0 items-center justify-between pl-4 pr-2 pt-[11px]">
            <h2 className="text-xl font-normal leading-[23px] text-black dark:text-text-primary">Manage</h2>
            <button type="button" aria-label="Close manage panel" onClick={closeManage} className="flex h-8 w-8 items-center justify-center rounded-full text-black/40 hover:bg-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus">
              <X aria-hidden className="h-4 w-4" />
            </button>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto px-4 pb-4 pt-[23px] [scrollbar-width:none]">{manageContents}</div>
        </section>
      ) : null}
    </div>
  );
}
