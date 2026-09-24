import { Pencil, Plus, Search, UserCheck, UserX } from "lucide-react";
import { useMemo, useState } from "react";

import { ManagePageHeader, MANAGE_PRIMARY_ACTION } from "@/components/layout";
import { ErrorState, Modal, Spinner } from "@/components/ui";
import { useSetUserActive, useUsers } from "@/features/admin/api";
import type { User } from "@/features/admin/types";
import { UserFormDialog } from "@/features/admin/UserFormDialog";
import { QuickGuide, ROW_ICON } from "@/features/settings/QuickGuide";
import { apiErrorMessage } from "@/lib/api/errors";
import { useAuth } from "@/lib/auth";
import { formatDateTime } from "@/lib/format";

const ROLE_LABELS: Record<string, string> = {
  owner: "Owner",
  admin: "Admin",
  manager: "Manager",
  agent: "Agent",
  viewer: "Viewer",
};

function roleLabel(member: User): string {
  if (member.is_superuser) return "Owner";
  const role = member.roles[0];
  if (!role) return "No role";
  return ROLE_LABELS[role] ?? role.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

/** "Online" for someone signed in within the last 15 minutes, else when they were last seen. */
function presence(member: User): { online: boolean; label: string } {
  if (!member.is_active) return { online: false, label: "Cannot sign in" };
  if (!member.last_login_at) return { online: false, label: "Never signed in" };
  const minutes = (Date.now() - new Date(member.last_login_at).getTime()) / 60_000;
  if (minutes < 15) return { online: true, label: "Online" };
  return { online: false, label: `Last seen ${formatDateTime(member.last_login_at)}` };
}

/** Manage → Team, laid out as the reference: a quota strip and one card per team member. */
export function TeamPage(): JSX.Element {
  const { user: me, hasPermission } = useAuth();
  const canManage = hasPermission("users:manage");
  const users = useUsers();
  const setActive = useSetUserActive();
  const [search, setSearch] = useState("");
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [disabling, setDisabling] = useState<User | null>(null);

  const members = useMemo(() => users.data?.data ?? [], [users.data]);
  const activeCount = members.filter((member) => member.is_active).length;
  const shown = members.filter((member) => {
    const needle = search.trim().toLowerCase();
    return !needle || member.full_name.toLowerCase().includes(needle) || member.email.toLowerCase().includes(needle);
  });

  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader title="Team Members" />
      <div className="mx-auto max-w-[1000px] space-y-5 px-4 py-6 sm:px-[45px]">
        <QuickGuide
          eyebrow="Agent quick guide"
          text="Add the people who chat with customers. Each person signs in with their own email, and their role decides what they can see and change."
        />

        <div className="flex flex-wrap items-center gap-4 rounded-[8px] bg-surface p-5">
          <span className="flex h-12 w-12 items-center justify-center rounded-full bg-[#ebf5f3] text-[var(--color-nav-bg)] dark:bg-accent-soft dark:text-accent">
            <UserCheck aria-hidden className="h-6 w-6" />
          </span>
          <div>
            <p className="text-sm text-[#6e6e6e] dark:text-text-secondary">Team members</p>
            <p className="text-xl font-semibold text-black dark:text-text-primary">
              {activeCount} <span className="text-sm font-normal text-[#6e6e6e]">active of {members.length}</span>
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <p className="text-sm text-[#6e6e6e] dark:text-text-secondary">Team management dashboard</p>
          <div className="ml-auto flex h-[38px] w-full max-w-[240px] items-center gap-2 rounded-[8px] bg-surface px-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
            <Search aria-hidden className="h-4 w-4 shrink-0 text-black/40" />
            <input
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search by team member"
              aria-label="Search team members"
              className="h-full min-w-0 flex-1 bg-transparent text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus:outline-none dark:text-text-primary"
            />
          </div>
          {canManage ? (
            <button type="button" onClick={() => setCreating(true)} className={MANAGE_PRIMARY_ACTION}>
              <Plus aria-hidden className="mr-1 h-4 w-4" /> Add Team Member
            </button>
          ) : null}
        </div>

        {users.isLoading ? (
          <Spinner label="Loading team members…" />
        ) : users.isError ? (
          <ErrorState message={apiErrorMessage(users.error)} onRetry={() => void users.refetch()} />
        ) : shown.length === 0 ? (
          <p className="rounded-[8px] bg-surface py-10 text-center text-sm text-[#6e6e6e]">No team member matches this search.</p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2">
            {shown.map((member) => {
              const status = presence(member);
              const self = member.id === me?.id;
              return (
                <li key={member.id} className={`rounded-[8px] bg-surface p-5 ${member.is_active ? "" : "opacity-70"}`}>
                  <div className="flex items-center gap-3">
                    <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-[#f5efdf] text-lg text-[var(--color-nav-bg)]">
                      {member.full_name.trim()[0]?.toUpperCase() ?? "?"}
                    </span>
                    <p className="min-w-0 flex-1 truncate text-base text-[var(--color-nav-bg)] dark:text-accent">
                      {member.full_name}
                      {self ? <span className="ml-1 text-xs text-[#808080]">(you)</span> : null}
                    </p>
                    {canManage ? (
                      <div className="flex gap-1">
                        <button type="button" aria-label={`Edit ${member.full_name}`} title="Edit" onClick={() => setEditing(member)} className={ROW_ICON}>
                          <Pencil aria-hidden className="h-[17px] w-[17px]" />
                        </button>
                        {!self && !member.is_superuser ? (
                          member.is_active ? (
                            <button
                              type="button"
                              aria-label={`Stop ${member.full_name} signing in`}
                              title="Stop this person signing in"
                              onClick={() => setDisabling(member)}
                              className={`${ROW_ICON} hover:!bg-danger-soft hover:!text-danger`}
                            >
                              <UserX aria-hidden className="h-[17px] w-[17px]" />
                            </button>
                          ) : (
                            <button
                              type="button"
                              aria-label={`Let ${member.full_name} sign in again`}
                              title="Let this person sign in again"
                              onClick={() => setActive.mutate({ userId: member.id, active: true })}
                              className={ROW_ICON}
                            >
                              <UserCheck aria-hidden className="h-[17px] w-[17px]" />
                            </button>
                          )
                        ) : null}
                      </div>
                    ) : null}
                  </div>
                  <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
                    <div className="min-w-0">
                      <dt className="text-xs text-[#808080]">Username</dt>
                      <dd className="truncate text-black dark:text-text-primary">{member.email}</dd>
                    </div>
                    <div>
                      <dt className="text-xs text-[#808080]">Status</dt>
                      <dd className="flex items-center gap-1.5 text-black dark:text-text-primary">
                        <span aria-hidden className={`h-2 w-2 rounded-full ${status.online ? "bg-[#28c152]" : "bg-[#c4c4c4]"}`} />
                        <span className="truncate">{status.label}</span>
                      </dd>
                    </div>
                  </dl>
                  <p className="mt-4 text-sm font-medium text-[var(--color-nav-bg)] dark:text-accent">{roleLabel(member)}</p>
                </li>
              );
            })}
          </ul>
        )}
        {setActive.error ? <ErrorState message={apiErrorMessage(setActive.error)} /> : null}
      </div>

      {creating ? <UserFormDialog onClose={() => setCreating(false)} /> : null}
      {editing ? <UserFormDialog user={editing} onClose={() => setEditing(null)} /> : null}
      {disabling ? (
        <Modal title={`Stop ${disabling.full_name} signing in?`} onClose={() => setDisabling(null)}>
          <p className="text-sm text-text-secondary">
            They will be signed out and cannot sign in until you turn their access back on. Their chats and history stay.
          </p>
          <div className="mt-5 flex justify-end gap-2 border-t border-border pt-4">
            <button type="button" onClick={() => setDisabling(null)} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover">Cancel</button>
            <button
              type="button"
              disabled={setActive.isPending}
              onClick={() => setActive.mutate({ userId: disabling.id, active: false }, { onSuccess: () => setDisabling(null) })}
              className="h-9 rounded-md bg-danger px-4 text-sm font-medium text-white disabled:opacity-60"
            >
              Stop sign-in
            </button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
