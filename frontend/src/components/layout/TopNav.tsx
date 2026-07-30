import {
  Bell,
  ChevronDown,
  Contact,
  Menu,
  MessageSquareText,
  Moon,
  PanelLeftClose,
  PanelLeftOpen,
  Plus,
  Search,
  Sun,
  TriangleAlert,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { CommandPalette } from "@/features/global-search";
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
  onOpenMobileNav: () => void;
  onToggleCollapse: () => void;
}

const iconBtn =
  "flex h-10 w-10 items-center justify-center rounded-xl text-text-secondary transition-colors hover:bg-hover hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";

function isTypingTarget(target: EventTarget | null): boolean {
  return target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;
}

export function TopNav({ collapsed, onOpenMobileNav, onToggleCollapse }: TopNavProps): JSX.Element {
  const { resolvedTheme, toggle } = useTheme();
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const canSystem = hasPermission("system:read");
  const queues = useQueues(canSystem);
  const [accountOpen, setAccountOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [attentionOpen, setAttentionOpen] = useState(false);
  const [helpOpen, setHelpOpen] = useState(false);

  const queueDepth = (queues.data?.queues ?? []).reduce((sum, queue) => sum + queue.depth, 0);
  const parked = queues.data?.dead_letter_parked ?? 0;
  const noWorkers = canSystem && Boolean(queues.data) && (queues.data?.workers.length ?? 0) === 0;
  const attentionCount = (queueDepth > 100 ? 1 : 0) + (parked > 0 ? 1 : 0) + (noWorkers ? 1 : 0);

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

  const createActions = [
    hasPermission("campaigns:write")
      ? { label: "Campaign", description: "Build a broadcast", path: "/campaigns/new", icon: MessageSquareText }
      : null,
    hasPermission("templates:write")
      ? { label: "Template", description: "Create a Meta template", path: "/templates/new", icon: Plus }
      : null,
    hasPermission("contacts:import")
      ? { label: "Import contacts", description: "Upload CSV or Excel", path: "/contacts?import=1", icon: Contact }
      : null,
  ].filter((action): action is NonNullable<typeof action> => action !== null);

  return (
    <>
      <header className="relative z-30 flex h-14 shrink-0 items-center gap-2 border-b border-border bg-[color-mix(in_srgb,var(--color-bg-surface)_92%,transparent)] px-3 backdrop-blur-xl sm:px-4">
        <button type="button" aria-label="Open navigation" onClick={onOpenMobileNav} className={`${iconBtn} lg:hidden`}>
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
            <div className="relative hidden md:block">
              <button
                type="button"
                aria-haspopup="menu"
                aria-expanded={createOpen}
                onClick={() => setCreateOpen((open) => !open)}
                className="flex h-10 items-center gap-2 rounded-xl bg-accent px-3.5 text-sm font-medium text-accent-fg shadow-sm transition-colors hover:bg-accent-strong"
              >
                <Plus aria-hidden className="h-4 w-4" />
                Create
                <ChevronDown aria-hidden className="h-3.5 w-3.5" />
              </button>
              {createOpen ? (
                <div role="menu" className="absolute right-0 z-40 mt-2 w-64 rounded-2xl border border-border bg-surface p-2 shadow-lg">
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

          <button type="button" aria-label={`Attention center${attentionCount ? `, ${attentionCount} alerts` : ""}`} onClick={() => setAttentionOpen(true)} className={`relative ${iconBtn}`}>
            <Bell aria-hidden className="h-[18px] w-[18px]" />
            {attentionCount > 0 ? (
              <span className="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[9px] font-bold text-white ring-2 ring-surface">{attentionCount}</span>
            ) : null}
          </button>
          <div className="relative">
            <button
              type="button"
              aria-haspopup="menu"
              aria-expanded={accountOpen}
              aria-label="Account menu"
              onClick={() => setAccountOpen((open) => !open)}
              className="flex h-10 items-center gap-2 rounded-xl pl-1 pr-2 hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <span aria-hidden className="flex h-8 w-8 items-center justify-center rounded-xl bg-accent text-xs font-semibold text-accent-fg">{user ? initials(user.full_name) : "U"}</span>
              {user ? <span className="hidden max-w-[8rem] truncate text-sm font-medium text-text-primary xl:block">{user.full_name}</span> : null}
              <ChevronDown aria-hidden className="hidden h-3.5 w-3.5 text-text-disabled xl:block" />
            </button>
            {accountOpen ? (
              <div role="menu" className="absolute right-0 z-40 mt-2 w-64 overflow-hidden rounded-2xl border border-border bg-surface p-2 text-sm shadow-lg">
                {user ? (
                  <div className="mb-1 rounded-xl bg-surface-2 px-3 py-3">
                    <p className="truncate font-semibold text-text-primary">{user.full_name}</p>
                    <p className="truncate text-xs text-text-secondary">{user.email}</p>
                  </div>
                ) : null}
                <button type="button" role="menuitem" onClick={() => { setAccountOpen(false); navigate("/settings/preferences"); }} className="block w-full rounded-lg px-3 py-2 text-left text-text-primary hover:bg-hover">Preferences</button>
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

      {attentionOpen ? (
        <div className="fixed inset-0 z-[60] flex justify-end bg-black/35 backdrop-blur-sm">
          <button type="button" aria-label="Close attention center" onClick={() => setAttentionOpen(false)} className="absolute inset-0" />
          <aside role="dialog" aria-modal="true" aria-label="Attention center" className="relative z-10 h-full w-full max-w-md overflow-y-auto border-l border-border bg-surface p-5 shadow-lg">
            <div className="flex items-start justify-between gap-3">
              <div><h2 className="text-lg font-bold text-text-primary">Attention center</h2><p className="mt-1 text-sm text-text-secondary">Live operational signals that may need action.</p></div>
              <button type="button" aria-label="Close" onClick={() => setAttentionOpen(false)} className={iconBtn}><X aria-hidden className="h-4 w-4" /></button>
            </div>
            <div className="mt-6 space-y-3">
              {!canSystem ? <p className="rounded-xl border border-border bg-surface-2 p-4 text-sm text-text-secondary">No operational alerts are available for your role.</p> : null}
              {canSystem && attentionCount === 0 ? <p className="rounded-xl border border-success bg-success-soft p-4 text-sm text-success-on-soft">All monitored queues and workers look healthy.</p> : null}
              {noWorkers ? <Attention title="No workers online" description="Queued work cannot run until a worker reports a heartbeat." /> : null}
              {queueDepth > 100 ? <Attention title="Queue backlog needs review" description={`${queueDepth.toLocaleString()} tasks are waiting across the fleet.`} /> : null}
              {parked > 0 ? <Attention title="Dead-letter work present" description={`${parked.toLocaleString()} task${parked === 1 ? " is" : "s are"} parked for operator review.`} /> : null}
            </div>
            {canSystem ? <button type="button" onClick={() => { setAttentionOpen(false); navigate("/operations"); }} className="mt-6 w-full rounded-xl bg-accent px-4 py-2.5 text-sm font-medium text-accent-fg">Open Operations</button> : null}
          </aside>
        </div>
      ) : null}

      {helpOpen ? (
        <div className="fixed inset-0 z-[60] grid place-items-center bg-black/40 p-4 backdrop-blur-sm">
          <button type="button" aria-label="Close shortcuts" onClick={() => setHelpOpen(false)} className="absolute inset-0" />
          <section role="dialog" aria-modal="true" aria-label="Keyboard shortcuts" className="relative z-10 w-full max-w-lg rounded-2xl border border-border bg-surface p-5 shadow-lg">
            <div className="flex items-start justify-between"><div><h2 className="text-lg font-bold text-text-primary">Work faster</h2><p className="mt-1 text-sm text-text-secondary">Keyboard shortcuts available across the workspace.</p></div><button type="button" aria-label="Close" onClick={() => setHelpOpen(false)} className={iconBtn}><X aria-hidden className="h-4 w-4" /></button></div>
            <dl className="mt-5 divide-y divide-border">
              {[['⌘ / Ctrl + K','Search and command palette'],['/','Search from any non-editing context'],['?','Open this shortcut guide'],['Esc','Close the active panel or dialog']].map(([key, label]) => <div key={key} className="flex items-center justify-between gap-4 py-3"><dt className="text-sm text-text-secondary">{label}</dt><dd><kbd className="rounded-lg border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-text-primary">{key}</kbd></dd></div>)}
            </dl>
          </section>
        </div>
      ) : null}
    </>
  );
}

function Attention({ title, description }: { title: string; description: string }): JSX.Element {
  return <div className="flex gap-3 rounded-xl border border-warning bg-warning-soft p-4"><TriangleAlert aria-hidden className="mt-0.5 h-5 w-5 shrink-0 text-warning-on-soft" /><div><p className="text-sm font-semibold text-text-primary">{title}</p><p className="mt-1 text-xs leading-relaxed text-text-secondary">{description}</p></div></div>;
}
