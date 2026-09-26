import { MessageSquareText, Pencil, Plus, Search, Star, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  Badge,
  Button,
  DefinitionRow,
  ErrorState,
  Field,
  Input,
  Modal,
  Select,
  Spinner,
  Textarea,
} from "@/components/ui";
import {
  apiErrorMessage,
  useCreateQuickReply,
  useDeleteQuickReply,
  useHasPermission,
  useQuickReplies,
  useUpdateQuickReply,
} from "@/features/settings/api";
import type { QuickReply, QuickReplyScopeFilter } from "@/features/settings/types";
import {
  MAX_BODY,
  MAX_SHORTCUT,
  MAX_TITLE,
  matchesQuickReplyFilter,
  previewQuickReplyBody,
  validateBody,
  validateShortcut,
  validateTitle,
} from "@/features/settings/types";
import { MANAGE_FIELD, MANAGE_OUTLINE, MANAGE_PRIMARY } from "@/features/settings/managePrimitives";
import { QuickGuide, ROW_ICON } from "@/features/settings/QuickGuide";
import { useFavouriteIds } from "@/features/settings/favourites";
import { formatCount } from "@/lib/format";

interface EditorState {
  /** The reply being amended, or `null` when creating a new one. */
  reply: QuickReply | null;
  shortcut: string;
  title: string;
  body: string;
  /** Fixed at creation; ignored by the update request and never edited afterwards. */
  shared: boolean;
}

function emptyEditor(): EditorState {
  // The create schema defaults `shared` to `false`, so personal is the form's default too.
  return { reply: null, shortcut: "", title: "", body: "", shared: false };
}

function editorFor(reply: QuickReply): EditorState {
  return { reply, shortcut: reply.shortcut, title: reply.title, body: reply.body, shared: reply.shared };
}

function ScopeBadge({ shared }: { shared: boolean }): JSX.Element {
  return <Badge tone={shared ? "accent" : "neutral"}>{shared ? "Shared" : "Personal"}</Badge>;
}

/**
 * Canned-message administration (Doc 04 §18.2).
 *
 * The `/shortcut` picker in the message composer could only ever read this list — it has no way to
 * create one, so on an organization with no replies yet the composer showed "No quick replies yet."
 * with nothing an agent could do about it. This screen is the missing other half of that contract.
 *
 * `usage_count` comes back from the read but no send path increments it yet, so it is left off the
 * table rather than presented as an analytic nothing currently produces.
 */
export function CannedMessagesPanel(): JSX.Element {
  const canManage = useHasPermission("inbox:write");
  const replies = useQuickReplies();
  const create = useCreateQuickReply();
  const update = useUpdateQuickReply();
  const remove = useDeleteQuickReply();

  const [search, setSearch] = useState("");
  const [scope, setScope] = useState<QuickReplyScopeFilter>("all");
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<QuickReply | null>(null);
  const [favourites, toggleFavourite] = useFavouriteIds("wa.canned-favourites.v1");

  const all = [...(replies.data ?? [])].sort((a, b) => a.shortcut.localeCompare(b.shortcut));
  const matching = all.filter((reply) => matchesQuickReplyFilter(reply, search, scope));
  const sharedCount = all.filter((reply) => reply.shared).length;

  const shortcutError = editor ? validateShortcut(editor.shortcut) : null;
  const titleError = editor ? validateTitle(editor.title) : null;
  const bodyError = editor ? validateBody(editor.body) : null;
  const editorValid = !shortcutError && !titleError && !bodyError;
  const saving = create.isPending || update.isPending;

  function openEditor(next: EditorState): void {
    // A previous failure must not resurface as a stale error the moment a different dialog opens.
    create.reset();
    update.reset();
    setEditor(next);
  }

  function openDeleteConfirm(reply: QuickReply): void {
    remove.reset();
    setConfirmDelete(reply);
  }

  function submitEditor(): void {
    if (!editor || !editorValid) return;

    const shortcut = editor.shortcut.trim();
    const title = editor.title.trim();
    const body = editor.body.trim();

    if (editor.reply) {
      update.mutate({ id: editor.reply.id, body: { shortcut, title, body } }, { onSuccess: () => setEditor(null) });
    } else {
      create.mutate({ shortcut, title, body, shared: editor.shared }, { onSuccess: () => setEditor(null) });
    }
  }

  if (replies.isLoading) return <Spinner label="Loading canned messages…" />;

  if (replies.isError) {
    return (
      <ErrorState message={apiErrorMessage(replies.error)} onRetry={() => void replies.refetch()} />
    );
  }

  const newReplyButton = canManage ? (
    <button type="button" aria-label="New canned message" onClick={() => openEditor(emptyEditor())} className={MANAGE_PRIMARY}>
      <Plus aria-hidden className="mr-1 h-4 w-4" /> Create
    </button>
  ) : null;

  const ordered = [...matching].sort((a, b) => Number(favourites.has(b.id)) - Number(favourites.has(a.id)));

  return (
    <div className="space-y-5">
      <QuickGuide
        eyebrow="Canned message quick guide"
        text="Save replies you send often and insert them in Live Chat: type / in the message box, or press Quick replies."
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-[38px] w-full max-w-[300px] items-center gap-2 rounded-[8px] bg-surface px-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <Search aria-hidden className="h-4 w-4 shrink-0 text-black/40" />
          <input
            id="canned-messages-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search canned message by name"
            aria-label="Search canned messages"
            className="h-full min-w-0 flex-1 bg-transparent text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus:outline-none dark:text-text-primary"
          />
        </div>
        <select
          aria-label="Filter by scope"
          value={scope}
          onChange={(event) => setScope(event.target.value as QuickReplyScopeFilter)}
          className={`${MANAGE_FIELD} h-[38px] w-[150px] pr-7`}
        >
          <option value="all">All</option>
          <option value="personal">Only me</option>
          <option value="shared">Whole team</option>
        </select>
        <span className="text-sm text-[#6e6e6e] dark:text-text-secondary">
          {formatCount(all.length)} saved · {formatCount(sharedCount)} for the whole team
        </span>
        <span className="ml-auto">{newReplyButton}</span>
      </div>

      <div className="overflow-x-auto rounded-[8px] bg-surface">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-[#f0f0f0] text-[13px] text-[var(--color-nav-bg)] dark:border-border dark:text-accent">
            <tr className="h-[50px]">
              <th scope="col" className="pl-6 pr-3 font-normal">Name</th>
              <th scope="col" className="px-3 font-normal">Type</th>
              <th scope="col" className="px-3 font-normal">Text</th>
              <th scope="col" className="hidden px-3 font-normal md:table-cell">Visible to</th>
              {canManage ? <th scope="col" className="px-3 text-center font-normal">Action</th> : null}
              <th scope="col" className="pl-3 pr-6 text-center font-normal">Favourite</th>
            </tr>
          </thead>
          <tbody>
            {all.length === 0 || ordered.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-12 text-center text-sm text-[#6e6e6e] dark:text-text-secondary">
                  {all.length === 0 ? (
                    <>
                      <MessageSquareText aria-hidden className="mx-auto mb-2 h-6 w-6 text-black/30" />
                      <p className="font-medium text-text-primary">No canned messages yet</p>
                      <p className="mt-1">
                        {canManage
                          ? "Press Create to save your first reply."
                          : "Nobody has saved a canned message yet. Ask an admin for access to add one."}
                      </p>
                    </>
                  ) : (
                    <>
                      <p className="font-medium text-text-primary">No canned messages match</p>
                      <button type="button" className={`${MANAGE_OUTLINE} mt-3`} onClick={() => { setSearch(""); setScope("all"); }}>
                        Clear filters
                      </button>
                    </>
                  )}
                </td>
              </tr>
            ) : (
              ordered.map((reply) => {
                const favourite = favourites.has(reply.id);
                return (
                  <tr key={reply.id} className="border-b border-[#f0f0f0] last:border-0 dark:border-border">
                    <td className="py-3 pl-6 pr-3 align-middle">
                      <p className="text-sm text-black dark:text-text-primary">{reply.title}</p>
                      <p className="font-mono text-xs text-[#808080]">/{reply.shortcut}</p>
                    </td>
                    <td className="px-3 align-middle text-[#4a4a4a] dark:text-text-secondary">Text</td>
                    <td className="max-w-[320px] px-3 align-middle text-xs text-[#6e6e6e] dark:text-text-secondary">
                      {previewQuickReplyBody(reply.body)}
                    </td>
                    <td className="hidden px-3 align-middle md:table-cell">
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${reply.shared ? "bg-[#ebf5f3] text-[var(--color-nav-bg)]" : "bg-[#f0f0f0] text-[#6e6e6e]"}`}>
                        {reply.shared ? "Whole team" : "Only me"}
                      </span>
                    </td>
                    {canManage ? (
                      <td className="px-3 align-middle">
                        <div className="flex justify-center gap-1">
                          <button type="button" aria-label={`Edit ${reply.title}`} title="Edit" onClick={() => openEditor(editorFor(reply))} className={ROW_ICON}>
                            <Pencil aria-hidden className="h-[17px] w-[17px]" />
                          </button>
                          <button type="button" aria-label={`Delete ${reply.title}`} title="Delete" onClick={() => openDeleteConfirm(reply)} className={`${ROW_ICON} hover:!bg-danger-soft hover:!text-danger`}>
                            <Trash2 aria-hidden className="h-[17px] w-[17px]" />
                          </button>
                        </div>
                      </td>
                    ) : null}
                    <td className="pl-3 pr-6 text-center align-middle">
                      <button
                        type="button"
                        aria-pressed={favourite}
                        aria-label={`${favourite ? "Remove" : "Mark"} ${reply.title} ${favourite ? "from" : "as"} favourite`}
                        onClick={() => toggleFavourite(reply.id)}
                        className={ROW_ICON}
                      >
                        <Star aria-hidden className={`h-[18px] w-[18px] ${favourite ? "fill-[#f5a623] text-[#f5a623]" : ""}`} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {!canManage ? (
        <p className="text-xs text-text-disabled">Read-only — adding or changing canned messages needs Live Chat edit access.</p>
      ) : null}

      {editor ? (
        <Modal
          title={editor.reply ? `Edit ${editor.reply.title}` : "New canned message"}
          onClose={() => setEditor(null)}
        >
          <form
            onSubmit={(event) => {
              event.preventDefault();
              submitEditor();
            }}
            className="space-y-4"
          >
            <Field
              htmlFor="canned-message-shortcut"
              label="Shortcut"
              error={editor.shortcut === "" ? null : shortcutError}
              description={`Up to ${MAX_SHORTCUT} characters. What an agent types after / to find it.`}
            >
              <Input
                id="canned-message-shortcut"
                value={editor.shortcut}
                maxLength={MAX_SHORTCUT}
                invalid={editor.shortcut !== "" && shortcutError !== null}
                onChange={(event) => setEditor({ ...editor, shortcut: event.target.value })}
              />
            </Field>

            <Field
              htmlFor="canned-message-title"
              label="Title"
              error={editor.title === "" ? null : titleError}
              description={`Up to ${MAX_TITLE} characters. Shown beside the shortcut in the picker.`}
            >
              <Input
                id="canned-message-title"
                value={editor.title}
                maxLength={MAX_TITLE}
                invalid={editor.title !== "" && titleError !== null}
                onChange={(event) => setEditor({ ...editor, title: event.target.value })}
              />
            </Field>

            <Field
              htmlFor="canned-message-body"
              label="Body"
              error={editor.body === "" ? null : bodyError}
              description={`${editor.body.length}/${MAX_BODY} characters.`}
            >
              <Textarea
                id="canned-message-body"
                value={editor.body}
                maxLength={MAX_BODY}
                invalid={editor.body !== "" && bodyError !== null}
                onChange={(event) => setEditor({ ...editor, body: event.target.value })}
              />
            </Field>

            <div>
              <p className="mb-1.5 text-xs font-semibold text-text-secondary">Message preview</p>
              <div
                aria-label="Message preview"
                className="min-h-20 rounded-xl border border-border bg-accent-soft p-3 text-sm leading-relaxed text-text-primary"
              >
                {editor.body.trim() || (
                  <span className="text-text-disabled">
                    Your message will appear here as you type. Selecting it later inserts the text
                    into the composer; it does not send automatically.
                  </span>
                )}
              </div>
            </div>

            {editor.reply ? (
              // Read-only information, not a control — a `label htmlFor` pointing at a `<div>` would
              // create no real accessible association, so this is a definition row instead of a fake
              // form field.
              <dl>
                <DefinitionRow label="Scope">
                  <div className="flex items-center gap-2">
                    <ScopeBadge shared={editor.reply.shared} />
                    <span className="text-xs text-text-secondary">
                      Set when a canned message is created and cannot be changed here.
                    </span>
                  </div>
                </DefinitionRow>
              </dl>
            ) : (
              <Field
                htmlFor="canned-message-shared"
                label="Scope"
                description="Personal is visible only to you; shared is visible to the whole team. This cannot be changed later."
              >
                <Select
                  id="canned-message-shared"
                  value={editor.shared ? "shared" : "personal"}
                  onChange={(event) => setEditor({ ...editor, shared: event.target.value === "shared" })}
                >
                  <option value="personal">Personal</option>
                  <option value="shared">Shared</option>
                </Select>
              </Field>
            )}

            {create.error || update.error ? (
              <ErrorState message={apiErrorMessage(create.error ?? update.error)} />
            ) : null}

            <div className="flex gap-2 border-t border-border pt-4">
              <Button
                type="button"
                variant="secondary"
                block
                disabled={saving}
                onClick={() => setEditor(null)}
              >
                Cancel
              </Button>
              <Button type="submit" block disabled={!editorValid || saving}>
                {saving ? "Saving…" : editor.reply ? "Save changes" : "Create canned message"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}

      {confirmDelete ? (
        <Modal title={`Delete ${confirmDelete.title}?`} onClose={() => setConfirmDelete(null)}>
          <p className="text-sm text-text-secondary">
            {confirmDelete.shared
              ? "This is a shared canned message — deleting it removes it for the whole team."
              : "This is a personal canned message, visible only to you."}{" "}
            Deleting a canned message cannot be undone.
          </p>

          {remove.error ? (
            <div className="mt-3">
              <ErrorState message={apiErrorMessage(remove.error)} />
            </div>
          ) : null}

          <div className="mt-5 flex gap-2 border-t border-border pt-4">
            <Button
              variant="secondary"
              block
              disabled={remove.isPending}
              onClick={() => setConfirmDelete(null)}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              block
              disabled={remove.isPending}
              onClick={() =>
                remove.mutate(confirmDelete.id, { onSuccess: () => setConfirmDelete(null) })
              }
            >
              {remove.isPending ? "Deleting…" : "Delete canned message"}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
