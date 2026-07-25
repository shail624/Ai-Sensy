import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  Contact,
  FileText,
  Hash,
  ListChecks,
  Megaphone,
  MessageSquareText,
  Search,
  Star,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ComponentType } from "react";
import { useNavigate } from "react-router-dom";

import { navItems, visibleNavItems } from "@/components/layout/navigation";
import { toListQuery } from "@/features/inbox/api";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import { useAuth } from "@/lib/auth";
import { useWorkspacePreferences } from "@/lib/workspace";

interface SearchResult {
  id: string;
  kind: string;
  label: string;
  description: string;
  path: string;
  icon: ComponentType<{ className?: string }>;
}

interface Props {
  open: boolean;
  onClose: () => void;
}

const MAX_RESULTS = 36;

async function settle<T>(promise: Promise<T>, fallback: T): Promise<T> {
  try {
    return await promise;
  } catch {
    return fallback;
  }
}

function contactLabel(contact: { full_name?: string | null; profile_name?: string | null; phone_e164: string }) {
  return contact.full_name ?? contact.profile_name ?? contact.phone_e164;
}

/**
 * Permission-scoped workspace search composed only from existing APIs. The backend has no unified
 * `/search` route, so this normalizes bounded reads without inventing a second contract. Message
 * results are explicitly the recent conversation previews currently exposed by the inbox API.
 */
function useWorkspaceSearch(term: string, enabled: boolean): SearchResult[] {
  const { hasPermission, user } = useAuth();
  const normalized = term.trim();
  const permissions = user?.permissions.join("|") ?? "";

  const query = useQuery({
    queryKey: ["workspace-search", normalized, permissions, user?.is_superuser],
    enabled: enabled && normalized.length >= 2,
    staleTime: 30_000,
    queryFn: async (): Promise<SearchResult[]> => {
      const lower = normalized.toLocaleLowerCase();
      const [contacts, campaigns, templates, numbers, users, tasks, media, conversations] = await Promise.all([
        hasPermission("contacts:read")
          ? settle(
              (async () =>
                unwrap(
                  await api.POST("/api/v1/contacts/search", {
                  body: {
                    match_type: "any",
                    rules: [
                      { group_index: 0, field_source: "contact", field_key: "full_name", operator: "contains", value: normalized },
                      { group_index: 0, field_source: "contact", field_key: "phone_e164", operator: "contains", value: normalized },
                      { group_index: 0, field_source: "contact", field_key: "email", operator: "contains", value: normalized },
                    ],
                    cursor: null,
                    limit: 8,
                  },
                  }),
                ).data)(),
              [],
            )
          : [],
        hasPermission("campaigns:read")
          ? settle((async () => unwrap(await api.GET("/api/v1/campaigns")).data)(), [])
          : [],
        hasPermission("templates:read")
          ? settle((async () => unwrap(await api.GET("/api/v1/templates")).data)(), [])
          : [],
        hasPermission("waba:read")
          ? settle((async () => unwrap(await api.GET("/api/v1/phone-numbers")).data)(), [])
          : [],
        hasPermission("users:read")
          ? settle((async () => unwrap(await api.GET("/api/v1/users")).data)(), [])
          : [],
        hasPermission("tasks:read")
          ? settle(
              (async () => unwrap(
                  await api.GET("/api/v1/tasks", { params: { query: { q: normalized, limit: 8 } } }),
                ).data)(),
              [],
            )
          : [],
        hasPermission("media:read")
          ? settle((async () => unwrap(await api.GET("/api/v1/media")).data)(), [])
          : [],
        hasPermission("inbox:read")
          ? settle(
              (async () => unwrap(
                await api.GET("/api/v1/conversations", {
                  params: { query: toListQuery({}, null, 100) },
                }),
              ).data)(),
              [],
            )
          : [],
      ]);

      const results: SearchResult[] = [];
      for (const contact of contacts) {
        results.push({
          id: `contact-${contact.id}`,
          kind: "Contacts",
          label: contactLabel(contact),
          description: [contact.phone_e164, contact.email].filter(Boolean).join(" · "),
          path: `/contacts/${contact.id}`,
          icon: Contact,
        });
      }
      for (const campaign of campaigns.filter((item) => item.name.toLocaleLowerCase().includes(lower)).slice(0, 6)) {
        results.push({
          id: `campaign-${campaign.id}`,
          kind: "Campaigns",
          label: campaign.name,
          description: `${campaign.status} · ${campaign.total_recipients.toLocaleString()} recipients`,
          path: `/campaigns/${campaign.id}`,
          icon: Megaphone,
        });
      }
      for (const template of templates.filter((item) => item.name.toLocaleLowerCase().includes(lower)).slice(0, 6)) {
        results.push({
          id: `template-${template.id}`,
          kind: "Templates",
          label: template.name,
          description: `${template.language} · ${template.category} · ${template.status}`,
          path: `/templates/${template.id}`,
          icon: MessageSquareText,
        });
      }
      for (const number of numbers.filter((item) =>
        `${item.display_number} ${item.verified_name ?? ""}`.toLocaleLowerCase().includes(lower),
      ).slice(0, 6)) {
        results.push({
          id: `number-${number.id}`,
          kind: "Numbers",
          label: number.verified_name ?? number.display_number,
          description: `${number.display_number} · ${number.status}`,
          path: `/channels/numbers/${number.id}`,
          icon: Hash,
        });
      }
      for (const account of users.filter((item) =>
        `${item.full_name} ${item.email}`.toLocaleLowerCase().includes(lower),
      ).slice(0, 6)) {
        results.push({
          id: `user-${account.id}`,
          kind: "Users",
          label: account.full_name,
          description: `${account.email} · ${account.is_active ? "Active" : "Inactive"}`,
          path: `/admin/users?q=${encodeURIComponent(account.email)}`,
          icon: UserRound,
        });
      }
      for (const task of tasks.slice(0, 6)) {
        results.push({
          id: `task-${task.id}`,
          kind: "Tasks",
          label: task.title,
          description: `${task.priority} priority · ${task.status}`,
          path: `/tasks?q=${encodeURIComponent(task.title)}`,
          icon: ListChecks,
        });
      }
      for (const asset of media.filter((item) =>
        `${item.file_name ?? ""} ${item.mime_type} ${item.sha256}`.toLocaleLowerCase().includes(lower),
      ).slice(0, 6)) {
        results.push({
          id: `document-${asset.id}`,
          kind: asset.media_type === "document" ? "Documents" : "Media",
          label: asset.file_name ?? `${asset.media_type} asset`,
          description: `${asset.mime_type} · ${Math.ceil(asset.byte_size / 1024).toLocaleString()} KB`,
          path: `/media/${asset.id}`,
          icon: FileText,
        });
      }
      for (const conversation of conversations.filter((item) =>
        (item.last_message_preview ?? "").toLocaleLowerCase().includes(lower),
      ).slice(0, 6)) {
        results.push({
          id: `message-${conversation.id}`,
          kind: "Recent messages",
          label: conversation.contact?.name ?? conversation.contact?.phone ?? "Conversation",
          description: conversation.last_message_preview ?? "Message",
          path: `/inbox?conversation=${conversation.id}`,
          icon: MessageSquareText,
        });
      }
      return results.slice(0, MAX_RESULTS);
    },
  });

  return query.data ?? [];
}

export function CommandPalette({ open, onClose }: Props): JSX.Element | null {
  const navigate = useNavigate();
  const { hasPermission, user } = useAuth();
  const workspace = useWorkspacePreferences(user?.id);
  const [term, setTerm] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const recordResults = useWorkspaceSearch(term, open);

  const navigationResults = useMemo<SearchResult[]>(() => {
    const lower = term.trim().toLocaleLowerCase();
    return visibleNavItems(hasPermission)
      .filter((item) => !lower || `${item.label} ${item.description}`.toLocaleLowerCase().includes(lower))
      .map((item) => ({
        id: `nav-${item.path}`,
        kind: "Navigate",
        label: item.label,
        description: item.description,
        path: item.path,
        icon: item.icon,
      }));
  }, [hasPermission, term]);

  const recentResults = useMemo<SearchResult[]>(() => {
    if (term.trim()) return [];
    return workspace.recents.map((item) => ({
      id: `recent-${item.path}`,
      kind: "Recently viewed",
      label: item.label,
      description: "Open recent workspace",
      path: item.path,
      icon: navItems.find((nav) => item.path === nav.path || item.path.startsWith(`${nav.path}/`))?.icon ?? ArrowRight,
    }));
  }, [term, workspace.recents]);

  const results = [...recentResults, ...navigationResults, ...recordResults].filter(
    (result, index, all) => all.findIndex((candidate) => candidate.path === result.path) === index,
  );

  useEffect(() => {
    if (!open) return;
    setTerm("");
    setActiveIndex(0);
    requestAnimationFrame(() => inputRef.current?.focus());
  }, [open]);

  useEffect(() => setActiveIndex(0), [term]);

  if (!open) return null;

  function choose(result: SearchResult): void {
    workspace.recordRecent({ label: result.label, path: result.path });
    navigate(result.path);
    onClose();
  }

  const active = Math.min(activeIndex, Math.max(results.length - 1, 0));

  return (
    <div className="fixed inset-0 z-[70] flex items-start justify-center bg-black/45 px-3 pt-[10vh] backdrop-blur-sm">
      <button type="button" aria-label="Close command palette" onClick={onClose} className="absolute inset-0" />
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Search and commands"
        className="relative z-10 flex max-h-[76vh] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-border bg-surface shadow-lg"
        onKeyDown={(event) => {
          if (event.key === "Escape") onClose();
          if (event.key === "ArrowDown") {
            event.preventDefault();
            setActiveIndex((index) => Math.min(index + 1, results.length - 1));
          }
          if (event.key === "ArrowUp") {
            event.preventDefault();
            setActiveIndex((index) => Math.max(index - 1, 0));
          }
          if (event.key === "Enter" && results[active]) {
            event.preventDefault();
            choose(results[active]);
          }
        }}
      >
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search aria-hidden className="h-5 w-5 shrink-0 text-text-disabled" />
          <label htmlFor="command-search" className="sr-only">Search the workspace</label>
          <input
            ref={inputRef}
            id="command-search"
            value={term}
            onChange={(event) => setTerm(event.target.value)}
            placeholder="Search contacts, campaigns, templates, numbers, tasks…"
            className="h-14 min-w-0 flex-1 bg-transparent text-base text-text-primary outline-none placeholder:text-text-disabled"
          />
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-lg p-2 text-text-secondary hover:bg-hover">
            <X aria-hidden className="h-4 w-4" />
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto p-2" role="listbox" aria-label="Search results">
          {results.length === 0 ? (
            <div className="px-5 py-12 text-center">
              <Search aria-hidden className="mx-auto h-8 w-8 text-text-disabled" />
              <p className="mt-3 text-sm font-semibold text-text-primary">
                {term.trim().length < 2 ? "Type at least two characters" : "No matching workspace items"}
              </p>
              <p className="mt-1 text-xs text-text-secondary">
                Search is permission-aware and only shows records you may open.
              </p>
            </div>
          ) : (
            results.map((result, index) => {
              const Icon = result.icon;
              const favorite = workspace.favorites.includes(result.path);
              return (
                <div
                  key={result.id}
                  role="option"
                  aria-selected={index === active}
                  className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 ${index === active ? "bg-accent-soft" : "hover:bg-hover"}`}
                >
                  <button type="button" onClick={() => choose(result)} className="flex min-w-0 flex-1 items-center gap-3 text-left">
                    <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-border bg-surface text-text-secondary">
                      <Icon aria-hidden className="h-4 w-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="flex items-center gap-2">
                        <span className="truncate text-sm font-medium text-text-primary">{result.label}</span>
                        <span className="shrink-0 rounded-full bg-surface-2 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-text-disabled">
                          {result.kind}
                        </span>
                      </span>
                      <span className="mt-0.5 block truncate text-xs text-text-secondary">{result.description}</span>
                    </span>
                  </button>
                  <button
                    type="button"
                    aria-label={favorite ? `Remove ${result.label} from favorites` : `Add ${result.label} to favorites`}
                    aria-pressed={favorite}
                    onClick={() => workspace.toggleFavorite(result.path)}
                    className={`rounded-lg p-2 ${favorite ? "text-warning" : "text-text-disabled opacity-0 group-hover:opacity-100 focus:opacity-100"}`}
                  >
                    <Star aria-hidden className={`h-4 w-4 ${favorite ? "fill-current" : ""}`} />
                  </button>
                </div>
              );
            })
          )}
        </div>

        <footer className="flex items-center justify-between border-t border-border bg-surface-2 px-4 py-2 text-[11px] text-text-disabled">
          <span>↑↓ move · Enter open · Esc close</span>
          <span>Recent message search covers the current inbox window</span>
        </footer>
      </section>
    </div>
  );
}
