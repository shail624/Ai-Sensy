import { MessageSquareText, Plus, Search } from "lucide-react";
import { useState } from "react";

import {
  Badge,
  Button,
  DefinitionRow,
  EmptyState,
  ErrorState,
  Field,
  FilterBar,
  Input,
  Modal,
  Section,
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
import { formatCount, formatDateTime } from "@/lib/format";

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
    <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => openEditor(emptyEditor())}>
      New canned message
    </Button>
  ) : null;

  return (
    <Section
      title="Canned Messages"
      description="Personal and shared quick replies an agent inserts into the message composer by /shortcut."
      action={newReplyButton}
    >
      <p className="mb-3 text-sm text-text-secondary">
        {all.length === 0
          ? "No canned messages exist yet."
          : `${formatCount(all.length)} canned message${all.length === 1 ? "" : "s"} · ${formatCount(sharedCount)} shared`}
      </p>

      {all.length > 0 ? (
        <div className="mb-3">
          <FilterBar label="Canned message search and filters" contentClassName="w-full">
            <Input
              id="canned-messages-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search shortcut, title or body…"
              aria-label="Search canned messages"
              leadingIcon={<Search aria-hidden className="h-4 w-4" />}
              containerClassName="min-w-0 flex-1 sm:min-w-[220px]"
            />
            <Select
              aria-label="Filter by scope"
              value={scope}
              onChange={(event) => setScope(event.target.value as QuickReplyScopeFilter)}
              className="min-w-[10rem] !w-auto"
            >
              <option value="all">All</option>
              <option value="personal">Personal</option>
              <option value="shared">Shared</option>
            </Select>
          </FilterBar>
        </div>
      ) : null}

      {all.length === 0 ? (
        <EmptyState
          icon={<MessageSquareText aria-hidden className="h-6 w-6" />}
          title="No canned messages yet"
          description={
            canManage
              ? "Create the first canned message so agents can insert it from the composer."
              : "Nobody has created a canned message yet. You need the inbox write permission to add one."
          }
          action={newReplyButton}
        />
      ) : matching.length === 0 ? (
        <EmptyState
          title="No canned messages match"
          description="No canned message matches this search and filter."
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setSearch("");
                setScope("all");
              }}
            >
              Clear filters
            </Button>
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
              <tr>
                <th scope="col" className="px-3 py-2">Shortcut</th>
                <th scope="col" className="px-3 py-2">Title</th>
                <th scope="col" className="px-3 py-2">Scope</th>
                <th scope="col" className="hidden px-3 py-2 md:table-cell">Body</th>
                <th scope="col" className="hidden px-3 py-2 lg:table-cell">Updated At</th>
                {canManage ? (
                  <th scope="col" className="px-3 py-2 text-right">Actions</th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {matching.map((reply) => (
                <tr key={reply.id} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 align-top font-mono text-xs text-text-primary">
                    {reply.shortcut}
                  </td>
                  <td className="px-3 py-2 align-top text-text-primary">{reply.title}</td>
                  <td className="px-3 py-2 align-top">
                    <ScopeBadge shared={reply.shared} />
                  </td>
                  <td className="hidden max-w-xs px-3 py-2 align-top text-xs text-text-secondary md:table-cell">
                    {previewQuickReplyBody(reply.body)}
                  </td>
                  <td className="hidden px-3 py-2 align-top text-xs text-text-secondary lg:table-cell">
                    {formatDateTime(reply.updated_at)}
                  </td>
                  {canManage ? (
                    <td className="px-3 py-2 align-top">
                      <div className="flex flex-wrap justify-end gap-1">
                        <Button
                          variant="secondary"
                          size="sm"
                          aria-label={`Edit ${reply.title}`}
                          onClick={() => openEditor(editorFor(reply))}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          aria-label={`Delete ${reply.title}`}
                          onClick={() => openDeleteConfirm(reply)}
                        >
                          Delete
                        </Button>
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {!canManage ? (
        <p className="mt-3 text-xs text-text-disabled">
          Read-only — changing canned messages needs the inbox write permission.
        </p>
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
    </Section>
  );
}
