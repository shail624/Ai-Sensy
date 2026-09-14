import {
  Bell,
  ChevronDown,
  Menu,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Sun,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";

import { visibleCreateActions } from "@/components/layout/navigation";
import { Modal } from "@/components/ui";
import { CommandPalette } from "@/features/global-search";
import { NotificationCenter, useUnreadCount } from "@/features/notifications";
import { useQueues } from "@/features/operations/api";
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
  mobileNavOpen: boolean;
  onOpenMobileNav: () => void;
  onToggleCollapse: () => void;
}

const iconBtn =
  "flex h-10 w-10 items-center justify-center rounded-xl text-text-secondary transition-colors hover:bg-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

function isTypingTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
}

export function TopNav({ collapsed, mobileNavOpen, onOpenMobileNav, onToggleCollapse }: TopNavProps): JSX.Element {
  const { resolvedTheme, toggle } = useTheme();
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const canSystem = hasPermission("system:read");
  const canReadNotifications = hasPermission("tasks:read");
  const canViewTeamNotifications = hasPermission("tasks:assign");
  const canViewUsers = hasPermission("users:read");
  const queues = useQueues(canSystem);
  const unread = useUnreadCount(canReadNotifications);
  const [accountOpen, setAccountOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [attentionOpen, setAttentionOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);
  const createMenuRef = useRef<HTMLDivElement>(null);
  const createButtonRef = useRef<HTMLButtonElement>(null);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const accountButtonRef = useRef<HTMLButtonElement>(null);
  const notificationButtonRef = useRef<HTMLButtonElement>(null);

  const queueDepth = (queues.data?.queues ?? []).reduce((sum, queue) => sum + queue.depth, 0);
  const parked = queues.data?.dead_letter_parked ?? 0;
  const noWorkers = canSystem && Boolean(queues.data) && (queues.data?.workers.length ?? 0) === 0;
  const unreadCount = unread.data?.unread ?? 0;
  const systemSignals = [
    ...(noWorkers ? [{ title: "No workers online", description: "Queued work cannot run until a worker reports a heartbeat." }] : []),
    ...(queueDepth > 100 ? [{ title: "Queue backlog needs review", description: `${queueDepth.toLocaleString()} tasks are waiting across the fleet.` }] : []),
    ...(parked > 0 ? [{ title: "Dead-letter work present", description: `${parked.toLocaleString()} task${parked === 1 ? " is" : "s are"} parked for operator review.` }] : []),
  ];

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent): void {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === "k") {
        event.preventDefault();
        setPaletteOpen(true);
        return;
      }
      if (event.key === "/" && !isTypingTarget(event.target)) {
        event.preventDefault();
        setPaletteOpen(true);
        return;
      }
      if (event.key === "?" && !isTypingTarget(event.target)) setHelpOpen(true);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    function onPointerDown(event: MouseEvent): void {
      const target = event.target as Node;
      if (createOpen && !createMenuRef.current?.contains(target)) setCreateOpen(false);
      if (accountOpen && !accountMenuRef.current?.contains(target)) setAccountOpen(false);
    }
    function onDismiss(event: KeyboardEvent): void {
      if (event.key !== "Escape") return;
      if (createOpen) {
        setCreateOpen(false);
        createButtonRef.current?.focus();
      } else if (accountOpen) {
        setAccountOpen(false);
        accountButtonRef.current?.focus();
      }
    }
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onDismiss);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onDismiss);
    };
  }, [accountOpen, createOpen]);

  const createActions = visibleCreateActions(hasPermission);

  return (
    <>
      <header className="relative z-30 flex h-14 shrink-0 items-center gap-2 border-b border-border bg-[color-mix(in_srgb,var(--color-bg-surface)_92%,transparent)] px-3 backdrop-blur-xl sm:px-4">
        <button
          type="button"
          aria-label="Open navigation"
          aria-controls="mobile-navigation"
          aria-expanded={mobileNavOpen}
          onClick={onOpenMobileNav}
          className={`${iconBtn} lg:hidden`}
        >
          <Menu aria-hidden className="h-[18px] w-[18px]" />
        </button>
        <button
          type="button"
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          onClick={onToggleCollapse}
          className={`hidden lg:flex ${iconBtn}`}
        >
          {collapsed ? <PanelLeftOpen aria-hidden className="h-[18px] w-[18px]" /> : <PanelLeftClose aria-hidden className="h-[18px] w-[18px]" />}
        </button>

        <button
          type="button"
          onClick={() => setPaletteOpen(true)}
          className="mr-auto flex h-9 min-w-0 max-w-sm flex-1 items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 text-left text-sm text-text-secondary transition-colors hover:border-border-strong hover:bg-hover md:ml-2 md:mr-5"
        >
          <Search aria-hidden className="h-4 w-4 shrink-0 text-text-disabled" />
          <span className="truncate">Search</span>
          <kbd className="ml-auto hidden rounded-md border border-border bg-surface px-1.5 py-0.5 font-mono text-[10px] text-text-disabled sm:inline">⌘K</kbd>
        </button>

        <div className="flex items-center gap-1">
          {createActions.length > 0 ? (
            <div ref={createMenuRef} className="relative hidden md:block">
              <button
                ref={createButtonRef}
                type="button"
                aria-haspopup="menu"
                aria-expanded={createOpen}
                aria-controls="create-menu"
                onClick={() => {
                  setAccountOpen(false);
                  setCreateOpen((open) => !open);
                }}
                className="flex h-10 items-center gap-2 rounded-xl bg-accent px-3.5 text-sm font-medium text-accent-fg shadow-sm transition-colors hover:bg-accent-strong"
              >
                <Plus aria-hidden className="h-4 w-4" />
                Create
                <ChevronDown aria-hidden className="h-3.5 w-3.5" />
              </button>
              {createOpen ? (
                <div id="create-menu" role="menu" aria-label="Create" className="absolute right-0 z-40 mt-2 w-72 rounded-2xl border border-border bg-surface p-2 shadow-lg">
                  {createActions.map((action) => {
                    const Icon = action.icon;
                    return (
                      <button
                        key={action.path}
                        type="button"
                        role="menuitem"
                        onClick={() => {
                          setCreateOpen(false);
                          navigate(action.path);
                        }}
                        className="flex w-full items-center gap-3 rounded-xl px-3 py-2 text-left hover:bg-hover"
                      >
                        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-accent-soft text-accent"><Icon aria-hidden className="h-4 w-4" /></span>
                        <span><span className="block text-sm font-medium text-text-primary">{action.label}</span><span className="block text-xs text-text-secondary">{action.description}</span></span>
                      </button>
                    );
                  })}
                </div>
              ) : null}
            </div>
          ) : null}

          <button ref={notificationButtonRef} type="button" aria-label={`Notification center${unreadCount ? `, ${unreadCount} unread` : ""}`} aria-expanded={attentionOpen} onClick={() => setAttentionOpen(true)} className={`relative ${iconBtn}`}>
            <Bell aria-hidden className="h-[18px] w-[18px]" />
            {unreadCount > 0 ? (
              <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[9px] font-bold text-white ring-2 ring-surface">{unreadCount > 99 ? "99+" : unreadCount}</span>
            ) : null}
          </button>
          <div ref={accountMenuRef} className="relative">
            <button
              ref={accountButtonRef}
              type="button"
              aria-haspopup="menu"
              aria-expanded={accountOpen}
              aria-label="Account menu"
              aria-controls="account-menu"
              onClick={() => {
                setCreateOpen(false);
                setAccountOpen((open) => !open);
              }}
              className="flex h-10 items-center gap-2 rounded-xl pl-1 pr-2 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-xl bg-accent text-xs font-semibold text-accent-fg">{user ? initials(user.full_name) : "U"}</span>
              {user ? <span className="hidden max-w-[8rem] truncate text-sm font-medium text-text-primary xl:block">{user.full_name}</span> : null}
              <ChevronDown aria-hidden className="hidden h-3.5 w-3.5 text-text-disabled xl:block" />
            </button>
            {accountOpen ? (
              <div id="account-menu" role="menu" aria-label="Account" className="absolute right-0 z-40 mt-2 w-64 overflow-hidden rounded-2xl border border-border bg-surface p-2 text-sm shadow-lg">
                {user ? (
                  <div className="mb-1 rounded-xl bg-surface-2 px-3 py-3">
                    <p className="truncate font-semibold text-text-primary">{user.full_name}</p>
                    <p className="truncate text-xs text-text-secondary">{user.email}</p>
                  </div>
                ) : null}
                {hasPermission("auth:self") ? <button type="button" role="menuitem" onClick={() => { setAccountOpen(false); navigate("/settings/preferences"); }} className="block w-full rounded-lg px-3 py-2 text-left text-text-primary hover:bg-hover">Preferences</button> : null}
                <button type="button" role="menuitem" onClick={() => { setAccountOpen(false); toggle(); }} className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-text-primary hover:bg-hover">
                  {resolvedTheme === "dark" ? <Sun aria-hidden className="h-4 w-4" /> : <Moon aria-hidden className="h-4 w-4" />}
                  Switch to {resolvedTheme === "dark" ? "light" : "dark"} mode
                </button>
                <button type="button" role="menuitem" onClick={() => { setAccountOpen(false); setHelpOpen(true); }} className="block w-full rounded-lg px-3 py-2 text-left text-text-primary hover:bg-hover">Keyboard shortcuts</button>
                <button type="button" role="menuitem" onClick={() => { setAccountOpen(false); void logout(); }} className="block w-full rounded-lg px-3 py-2 text-left text-danger hover:bg-danger-soft">Sign out</button>
              </div>
            ) : null}
          </div>
        </div>
      </header>

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />

      <NotificationCenter
        open={attentionOpen}
        onClose={() => {
          setAttentionOpen(false);
          notificationButtonRef.current?.focus();
        }}
        canRead={canReadNotifications}
        canViewTeam={canViewTeamNotifications}
        canViewUsers={canViewUsers}
        canViewSystem={canSystem}
        systemSignals={systemSignals}
      />

      {helpOpen ? (
        <Modal
          title="Keyboard shortcuts"
          onClose={() => {
            setHelpOpen(false);
            accountButtonRef.current?.focus();
          }}
          panelClassName="max-w-lg"
        >
          <p className="text-sm text-text-secondary">Keyboard shortcuts available across the workspace.</p>
          <dl className="mt-4 divide-y divide-border">
            {[
              ["⌘ / Ctrl + K", "Search and command palette"],
              ["/", "Search from any non-editing context"],
              ["?", "Open this shortcut guide"],
              ["Esc", "Close the active panel or dialog"],
            ].map(([key, label]) => (
              <div key={key} className="flex items-center justify-between gap-4 py-3">
                <dt className="text-sm text-text-secondary">{label}</dt>
                <dd>
                  <kbd className="rounded-lg border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-text-primary">
                    {key}
                  </kbd>
                </dd>
              </div>
            ))}
          </dl>
        </Modal>
      ) : null}
    </>
  );
}
