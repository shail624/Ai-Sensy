import {
  ArrowUpRight,
  Bell,
  CheckCheck,
  CircleAlert,
  RefreshCw,
  TriangleAlert,
  UserRound,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  FilterBar,
  Input,
  Modal,
  Select,
  Skeleton,
} from "@/components/ui";
import { useUsers } from "@/features/admin/api";
import {
  useMarkAllNotificationsRead,
  useMarkNotificationRead,
  useNotifications,
} from "@/features/notifications/api";
import {
  NOTIFICATION_STATUSES,
  NOTIFICATION_TYPES,
  type Notification,
  type NotificationListQuery,
} from "@/features/notifications/types";
import { apiErrorMessage } from "@/lib/api/errors";

interface SystemSignal {
  title: string;
  description: string;
}

interface NotificationCenterProps {
  open: boolean;
  onClose: () => void;
  canRead: boolean;
  canViewTeam: boolean;
  canViewUsers: boolean;
  systemSignals: SystemSignal[];
  canViewSystem: boolean;
}

export function NotificationCenter({
  open,
  onClose,
  canRead,
  canViewTeam,
  canViewUsers,
  systemSignals,
  canViewSystem,
}: NotificationCenterProps): JSX.Element | null {
  const navigate = useNavigate();
  const [online, setOnline] = useState(() => navigator.onLine);
  const [query, setQuery] = useState<NotificationListQuery>({ limit: 100 });
  const notifications = useNotifications(query, open && canRead && online);
  const markRead = useMarkNotificationRead();
  const markAll = useMarkAllNotificationsRead();
  const users = useUsers(open && canViewTeam && canViewUsers);

  useEffect(() => {
    const goOnline = (): void => setOnline(true);
    const goOffline = (): void => setOnline(false);
    window.addEventListener("online", goOnline);
    window.addEventListener("offline", goOffline);
    return () => {
      window.removeEventListener("online", goOnline);
      window.removeEventListener("offline", goOffline);
    };
  }, []);

  const assignees = useMemo(
    () => users.data?.data.filter((user) => user.is_active) ?? [],
    [users.data],
  );
  const isTeamView = Boolean(query.assignee_id);

  if (!open) return null;

  const setFilter = (key: keyof NotificationListQuery, value: string): void =>
    setQuery((current) => ({ ...current, [key]: value || undefined }));

  function openSource(item: Notification, target?: "contact" | "case" | "task"): void {
    if (!isTeamView && item.read_status === "unread") markRead.mutate(item.id);
    const path =
      target === "task" && item.task
        ? `/tasks?task=${item.task.id}`
        : target === "case" && item.reactivation_case
          ? `/reactivation/pipeline?case=${item.reactivation_case.id}`
          : item.contact
            ? `/contacts/${item.contact.id}`
            : item.reactivation_case
              ? `/reactivation/pipeline?case=${item.reactivation_case.id}`
              : item.task
                ? `/tasks?task=${item.task.id}`
                : null;
    if (path) {
      onClose();
      navigate(path);
    }
  }

  return (
    <Modal
      title="Notification center"
      onClose={onClose}
      variant="drawer"
      panelClassName="sm:max-w-xl"
      contentClassName="flex min-h-[calc(92vh-49px)] flex-col p-0 sm:min-h-[calc(100vh-49px)]"
    >
      <div className="border-b border-border px-4 py-4 sm:px-5">
        <p className="text-sm text-text-secondary">Your assigned work, dates, and case changes.</p>

        {canRead ? (
          <FilterBar
            label="Notification filters"
            className="mt-4"
            contentClassName="!grid w-full grid-cols-2 gap-2 sm:grid-cols-4"
          >
            <Select
              aria-label="Type"
              value={query.type ?? ""}
              onChange={(event) => setFilter("type", event.target.value)}
              controlSize="sm"
            >
              <option value="">All types</option>
              {NOTIFICATION_TYPES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Select
              aria-label="Status"
              value={query.status ?? ""}
              onChange={(event) => setFilter("status", event.target.value)}
              controlSize="sm"
            >
              <option value="">All status</option>
              {NOTIFICATION_STATUSES.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </Select>
            <Input
              aria-label="From date"
              type="date"
              value={query.date_from?.slice(0, 10) ?? ""}
              onChange={(event) =>
                setFilter(
                  "date_from",
                  event.target.value ? `${event.target.value}T00:00:00Z` : "",
                )
              }
              controlSize="sm"
            />
            <Input
              aria-label="To date"
              type="date"
              value={query.date_to?.slice(0, 10) ?? ""}
              onChange={(event) =>
                setFilter(
                  "date_to",
                  event.target.value ? `${event.target.value}T23:59:59Z` : "",
                )
              }
              controlSize="sm"
            />
            {canViewTeam && canViewUsers ? (
              <Select
                aria-label="Assignee"
                value={query.assignee_id ?? ""}
                onChange={(event) => setFilter("assignee_id", event.target.value)}
                controlSize="sm"
                className="col-span-2 sm:col-span-3"
              >
                <option value="">Assigned to me</option>
                {assignees.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </Select>
            ) : (
              <p className="col-span-2 self-center text-xs text-text-secondary sm:col-span-3">
                Showing notifications assigned to you
              </p>
            )}
            {isTeamView ? (
              <p className="self-center text-center text-xs text-text-secondary">
                Read-only team view
              </p>
            ) : (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={markAll.isPending}
                onClick={() => markAll.mutate(undefined)}
                leftIcon={<CheckCheck aria-hidden className="h-3.5 w-3.5" />}
                className="px-2 text-xs"
              >
                Mark all read
              </Button>
            )}
          </FilterBar>
        ) : null}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-5">
        {!online ? (
          <div
            role="status"
            className="mb-3 flex items-center gap-2 rounded-xl border border-warning bg-warning-soft p-3 text-sm text-warning-on-soft"
          >
            <CircleAlert aria-hidden className="h-4 w-4" />
            You are offline. Reconnect to refresh notifications.
          </div>
        ) : null}
        {!canRead ? (
          <EmptyState
            compact
            title="Notifications unavailable"
            description="Your role does not include access to assigned tasks."
            icon={<Bell aria-hidden className="h-6 w-6" />}
          />
        ) : null}
        {canRead && notifications.isLoading ? (
          <div aria-label="Loading notifications" className="space-y-3">
            {[1, 2, 3, 4].map((key) => (
              <div key={key} className="rounded-xl border border-border p-4">
                <Skeleton className="h-3 w-28" />
                <Skeleton className="mt-3 h-4 w-3/4" />
                <Skeleton className="mt-2 h-3 w-full" />
              </div>
            ))}
          </div>
        ) : null}
        {canRead && notifications.isError ? (
          <ErrorState
            message={apiErrorMessage(notifications.error)}
            onRetry={() => void notifications.refetch()}
          />
        ) : null}
        {canRead &&
        !notifications.isLoading &&
        !notifications.isError &&
        (notifications.data?.data.length ?? 0) === 0 ? (
          <EmptyState
            compact
            title="You are all caught up"
            description="New assignments, due work, and case changes will appear here."
            icon={<Bell aria-hidden className="h-6 w-6" />}
            action={
              <Button
                type="button"
                variant="secondary"
                onClick={() => void notifications.refetch()}
                leftIcon={<RefreshCw aria-hidden className="h-4 w-4" />}
              >
                Refresh
              </Button>
            }
          />
        ) : null}

        <ol className="space-y-2">
          {notifications.data?.data.map((item) => (
            <li
              key={item.id}
              className={`relative rounded-xl border p-4 transition-colors ${
                item.read_status === "unread"
                  ? "border-accent bg-accent-soft/40"
                  : "border-border bg-surface hover:bg-hover"
              }`}
            >
              <button
                type="button"
                aria-label={`Open ${item.title}`}
                onClick={() => openSource(item)}
                className="absolute inset-0 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              />
              <div className="pointer-events-none relative flex items-start gap-3">
                <span
                  className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${
                    item.read_status === "unread" ? "bg-accent" : "bg-border-strong"
                  }`}
                />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold text-text-primary">{item.title}</p>
                    <LifecycleBadge item={item} />
                  </div>
                  <p className="mt-1 text-sm leading-relaxed text-text-secondary">{item.body}</p>
                  {item.contact?.name ? (
                    <p className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-text-primary">
                      <UserRound aria-hidden className="h-3.5 w-3.5" />
                      {String(item.contact.name)}
                    </p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-xs text-text-secondary">
                    <time dateTime={item.created_at}>
                      {new Date(item.created_at).toLocaleString()}
                    </time>
                    {item.due_at ? <span>Due {new Date(item.due_at).toLocaleString()}</span> : null}
                  </div>
                  <div className="pointer-events-auto relative mt-3 flex flex-wrap gap-2">
                    {item.contact ? (
                      <SourceButton
                        label="Customer 360"
                        onClick={() => openSource(item, "contact")}
                      />
                    ) : null}
                    {item.reactivation_case ? (
                      <SourceButton label="Case" onClick={() => openSource(item, "case")} />
                    ) : null}
                    {item.task ? (
                      <SourceButton label="Task" onClick={() => openSource(item, "task")} />
                    ) : null}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ol>

        {canViewSystem ? (
          <section aria-label="System health" className="mt-6 border-t border-border pt-5">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-text-secondary">
              System health
            </h3>
            {systemSignals.length === 0 ? (
              <p className="mt-3 rounded-xl border border-success bg-success-soft p-3 text-sm text-success-on-soft">
                Monitored queues and workers look healthy.
              </p>
            ) : (
              <div className="mt-3 space-y-2">
                {systemSignals.map((signal) => (
                  <div
                    key={signal.title}
                    className="flex gap-3 rounded-xl border border-warning bg-warning-soft p-3"
                  >
                    <TriangleAlert
                      aria-hidden
                      className="mt-0.5 h-4 w-4 shrink-0 text-warning-on-soft"
                    />
                    <div>
                      <p className="text-sm font-semibold text-text-primary">{signal.title}</p>
                      <p className="mt-1 text-xs text-text-secondary">{signal.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => {
                onClose();
                navigate("/operations");
              }}
              rightIcon={<ArrowUpRight aria-hidden className="h-4 w-4" />}
              className="mt-3 px-0 text-accent"
            >
              Open Operations
            </Button>
          </section>
        ) : null}
      </div>
    </Modal>
  );
}

function LifecycleBadge({ item }: { item: Notification }): JSX.Element {
  const tone =
    item.lifecycle_status === "overdue"
      ? "danger"
      : item.lifecycle_status === "due_today"
        ? "warning"
        : item.lifecycle_status === "resolved"
          ? "success"
          : "neutral";
  return <Badge tone={tone}>{item.lifecycle_status.replace("_", " ")}</Badge>;
}

function SourceButton({ label, onClick }: { label: string; onClick: () => void }): JSX.Element {
  return (
    <Button
      type="button"
      variant="secondary"
      size="sm"
      onClick={onClick}
      rightIcon={<ArrowUpRight aria-hidden className="h-3 w-3" />}
      className="h-7 px-2 text-xs max-md:h-9"
    >
      {label}
    </Button>
  );
}
