import { Pencil, Plus, Search, Tag as TagIcon, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  Pagination,
  Spinner,
  TagChip,
} from "@/components/ui";
import {
  apiErrorMessage,
  useCreateTag,
  useDeleteTag,
  useHasPermission,
  useTags,
  useUpdateTag,
} from "@/features/settings/api";
import type { Tag, TagUsageFilter } from "@/features/settings/types";
import {
  MAX_TAG_DESCRIPTION,
  MAX_TAG_NAME,
  matchesTagFilter,
  validateTagColor,
  validateTagDescription,
  validateTagName,
} from "@/features/settings/types";
import { MANAGE_FIELD, MANAGE_PRIMARY } from "@/features/settings/managePrimitives";
import { QuickGuide, ROW_ICON } from "@/features/settings/QuickGuide";
import { formatCount, formatDateTime } from "@/lib/format";

/** The list endpoint returns every tag at once, so paging is done here to keep the table readable. */
const PAGE_SIZE = 25;

interface EditorState {
  /** The tag being amended, or `null` when creating a new one. */
  tag: Tag | null;
  name: string;
  color: string;
  description: string;
  firstMessageEnabled: boolean;
  firstMessageKeywords: string;
}

function emptyEditor(): EditorState {
  return {
    tag: null,
    name: "",
    color: "",
    description: "",
    firstMessageEnabled: false,
    firstMessageKeywords: "",
  };
}

function editorFor(tag: Tag): EditorState {
  return {
    tag,
    name: tag.name,
    color: tag.color ?? "",
    description: tag.description ?? "",
    firstMessageEnabled: tag.first_message_enabled,
    firstMessageKeywords: tag.first_message_keywords.join(", "),
  };
}

function keywordList(value: string): string[] {
  return value
    .split(/[\n,]/)
    .map((keyword) => keyword.trim())
    .filter(Boolean);
}

/**
 * Tag administration.
 *
 * The tag vocabulary was reachable only through the API before this screen existed: contacts and
 * conversations could attach tags, but attaching takes the id of a tag that already exists, so with
 * no way to create one the pickers stayed empty on a new organization.
 *
 * Tags carry no status column, so the second filter is usage — which is the question an operator
 * actually has, since an unused tag is the one worth renaming or removing.
 */
export function TagsPanel(): JSX.Element {
  const canManage = useHasPermission("contacts:write");
  const tags = useTags();
  const create = useCreateTag();
  const update = useUpdateTag();
  const remove = useDeleteTag();

  const [search, setSearch] = useState("");
  const [usage, setUsage] = useState<TagUsageFilter>("all");
  const [page, setPage] = useState(0);
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<Tag | null>(null);

  const all = useMemo(
    () => [...(tags.data ?? [])].sort((a, b) => a.name.localeCompare(b.name)),
    [tags.data],
  );
  const matching = useMemo(
    () => all.filter((tag) => matchesTagFilter(tag, search, usage)),
    [all, search, usage],
  );

  const pageCount = Math.max(1, Math.ceil(matching.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const rows = matching.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const inUse = all.filter((tag) => tag.usage_count > 0).length;

  const nameError = editor ? validateTagName(editor.name) : null;
  const colorError = editor ? validateTagColor(editor.color) : null;
  const descriptionError = editor ? validateTagDescription(editor.description) : null;
  const firstMessageKeywords = editor ? keywordList(editor.firstMessageKeywords) : [];
  const ruleError =
    editor?.firstMessageEnabled && firstMessageKeywords.length === 0
      ? "Add at least one exact-match keyword."
      : null;
  const editorValid = !nameError && !colorError && !descriptionError && !ruleError;
  const saving = create.isPending || update.isPending;

  // A changed filter has to return to the first page, or the results can land outside the view.
  function narrow(next: () => void): void {
    next();
    setPage(0);
  }

  function submitEditor(): void {
    if (!editor || !editorValid) return;

    const body = {
      name: editor.name.trim(),
      color: editor.color.trim() === "" ? null : editor.color.trim(),
      description: editor.description.trim() === "" ? null : editor.description.trim(),
      first_message_enabled: editor.firstMessageEnabled,
      first_message_keywords: firstMessageKeywords,
    };

    if (editor.tag) {
      update.mutate(
        { id: editor.tag.id, body },
        { onSuccess: () => setEditor(null) },
      );
    } else {
      create.mutate(body, { onSuccess: () => setEditor(null) });
    }
  }

  if (tags.isLoading) return <Spinner label="Loading tags…" />;

  if (tags.isError) {
    return <ErrorState message={apiErrorMessage(tags.error)} onRetry={() => void tags.refetch()} />;
  }

  // A previous failure must not resurface as a stale error the moment an unrelated dialog reopens.
  function openEditor(next: EditorState): void {
    create.reset();
    update.reset();
    setEditor(next);
  }

  function openDeleteConfirm(tag: Tag): void {
    remove.reset();
    setConfirmDelete(tag);
  }

  const newTagButton = canManage ? (
    <button type="button" aria-label="New tag" onClick={() => openEditor(emptyEditor())} className={MANAGE_PRIMARY}>
      <Plus aria-hidden className="mr-1 h-4 w-4" /> Create
    </button>
  ) : null;

  return (
    <div className="space-y-5">
      <QuickGuide
        eyebrow="Tag quick guide"
        text="Tags group your customers (for example by offer or interest). A first message tag is added automatically when a customer's first message matches its keywords."
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex h-[38px] w-full max-w-[300px] items-center gap-2 rounded-[8px] bg-surface px-3 shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <Search aria-hidden className="h-4 w-4 shrink-0 text-black/40" />
          <input
            id="tags-search"
            type="search"
            value={search}
            onChange={(event) => narrow(() => setSearch(event.target.value))}
            placeholder="Search by name & description"
            aria-label="Search tags"
            className="h-full min-w-0 flex-1 bg-transparent text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus:outline-none dark:text-text-primary"
          />
        </div>
        <select
          aria-label="Filter by usage"
          value={usage}
          onChange={(event) => narrow(() => setUsage(event.target.value as TagUsageFilter))}
          className={`${MANAGE_FIELD} h-[38px] w-[160px] pr-7`}
        >
          <option value="all">All</option>
          <option value="used">In use</option>
          <option value="unused">Unused</option>
        </select>
        <span className="text-sm text-[#6e6e6e] dark:text-text-secondary">
          {all.length === 0
            ? "No tags exist yet."
            : `${formatCount(all.length)} tag${all.length === 1 ? "" : "s"} · ${formatCount(inUse)} in use`}
        </span>
        <span className="ml-auto">{newTagButton}</span>
      </div>

      {all.length === 0 ? (
        <EmptyState
          icon={<TagIcon aria-hidden className="h-6 w-6" />}
          title="No tags yet"
          description={
            canManage
              ? "Create the first tag to start grouping contacts and conversations."
              : "Nobody has created a tag yet. You need the contacts write permission to add one."
          }
          action={newTagButton}
        />
      ) : matching.length === 0 ? (
        <EmptyState
          title="No tags match"
          description="No tag matches this search and filter."
          action={
            <Button
              variant="secondary"
              onClick={() =>
                narrow(() => {
                  setSearch("");
                  setUsage("all");
                })
              }
            >
              Clear filters
            </Button>
          }
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-[8px] bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-[#f0f0f0] text-[13px] text-[var(--color-nav-bg)] dark:border-border dark:text-accent">
                <tr className="h-[50px]">
                  <th scope="col" className="pl-6 pr-3 font-normal">
                    Tag Name
                  </th>
                  <th scope="col" className="hidden px-3 font-normal md:table-cell">
                    First Message
                  </th>
                  <th scope="col" className="px-3 font-normal">
                    Customers
                  </th>
                  <th scope="col" className="hidden px-3 font-normal lg:table-cell">
                    Last updated
                  </th>
                  {canManage ? (
                    <th scope="col" className="pl-3 pr-6 text-center font-normal">
                      Action
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {rows.map((tag) => (
                  <tr key={tag.id} className="border-b border-[#f0f0f0] last:border-0 dark:border-border">
                    <td className="py-3 pl-6 pr-3 align-middle">
                      <TagChip name={tag.name} color={tag.color} />
                      {tag.description ? (
                        <p className="mt-1 max-w-md text-xs text-text-secondary">
                          {tag.description}
                        </p>
                      ) : null}
                    </td>

                    <td className="hidden px-3 py-2 align-top md:table-cell">
                      {tag.first_message_enabled ? (
                        <div className="space-y-1">
                          <Badge tone="accent">Enabled</Badge>
                          <p className="text-xs text-text-secondary">
                            {formatCount(tag.first_message_keywords.length)} exact
                            {tag.first_message_keywords.length === 1 ? " match" : " matches"}
                          </p>
                        </div>
                      ) : (
                        <span className="text-xs text-text-disabled">Not configured</span>
                      )}
                    </td>

                    <td className="px-3 py-2 align-top">
                      {tag.usage_count > 0 ? (
                        <Badge tone="accent">
                          {formatCount(tag.usage_count)} contact
                          {tag.usage_count === 1 ? "" : "s"}
                        </Badge>
                      ) : (
                        <span className="text-xs text-text-disabled">Unused</span>
                      )}
                    </td>

                    <td className="hidden px-3 py-2 align-top text-xs text-text-secondary lg:table-cell">
                      {formatDateTime(tag.updated_at)}
                    </td>

                    {canManage ? (
                      <td className="px-3 py-2 align-top">
                        <div className="flex justify-center gap-1">
                          <button
                            type="button"
                            aria-label={`Edit ${tag.name}`}
                            title="Edit"
                            onClick={() => openEditor(editorFor(tag))}
                            className={ROW_ICON}
                          >
                            <Pencil aria-hidden className="h-[17px] w-[17px]" />
                          </button>
                          <button
                            type="button"
                            aria-label={`Delete ${tag.name}`}
                            title="Delete"
                            onClick={() => openDeleteConfirm(tag)}
                            className={`${ROW_ICON} hover:!bg-danger-soft hover:!text-danger`}
                          >
                            <Trash2 aria-hidden className="h-[17px] w-[17px]" />
                          </button>
                        </div>
                      </td>
                    ) : null}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {matching.length > PAGE_SIZE ? (
            <div className="mt-3">
              <Pagination
                label="Tag pages"
                hasPrevious={safePage > 0}
                hasNext={safePage < pageCount - 1}
                onPrevious={() => setPage(safePage - 1)}
                onNext={() => setPage(safePage + 1)}
                summary={`${formatCount(safePage * PAGE_SIZE + 1)}–${formatCount(
                  safePage * PAGE_SIZE + rows.length,
                )} of ${formatCount(matching.length)}`}
              />
            </div>
          ) : null}
        </>
      )}

      {!canManage ? (
        <p className="mt-3 text-xs text-text-disabled">
          Read-only — changing tags needs the contacts write permission.
        </p>
      ) : null}

      {editor ? (
        <Modal
          title={editor.tag ? `Edit ${editor.tag.name}` : "New tag"}
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
              htmlFor="tag-name"
              label="Name"
              error={editor.name === "" ? null : nameError}
              description={`Up to ${MAX_TAG_NAME} characters. Names are unique.`}
            >
              <Input
                id="tag-name"
                value={editor.name}
                maxLength={MAX_TAG_NAME}
                invalid={editor.name !== "" && nameError !== null}
                onChange={(event) => setEditor({ ...editor, name: event.target.value })}
              />
            </Field>

            <Field
              htmlFor="tag-color"
              label="Colour"
              optional
              error={colorError}
              description="A hex value such as #1F6FEB. Leave empty for no colour."
            >
              <Input
                id="tag-color"
                value={editor.color}
                placeholder="#1F6FEB"
                invalid={colorError !== null}
                onChange={(event) => setEditor({ ...editor, color: event.target.value })}
              />
            </Field>

            <Field
              htmlFor="tag-description"
              label="Description"
              optional
              error={descriptionError}
              description={`${editor.description.length}/${MAX_TAG_DESCRIPTION}`}
            >
              <Input
                id="tag-description"
                value={editor.description}
                maxLength={MAX_TAG_DESCRIPTION}
                invalid={descriptionError !== null}
                onChange={(event) => setEditor({ ...editor, description: event.target.value })}
              />
            </Field>

            <div className="rounded-xl border border-border bg-surface-2 p-4">
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  type="checkbox"
                  aria-label="Apply on matching first message"
                  checked={editor.firstMessageEnabled}
                  onChange={(event) =>
                    setEditor({ ...editor, firstMessageEnabled: event.target.checked })
                  }
                  className="mt-0.5 h-4 w-4 accent-[var(--color-accent)]"
                />
                <span>
                  <span className="block text-sm font-semibold text-text-primary">
                    Apply on matching first message
                  </span>
                  <span className="mt-1 block text-xs text-text-secondary">
                    Applies this tag once when a contact&apos;s first inbound message exactly matches.
                  </span>
                </span>
              </label>
              <Field
                htmlFor="tag-first-message-keywords"
                label="First-message keywords"
                description="Comma-separated; matching ignores case and surrounding spaces."
                error={ruleError}
              >
                <Input
                  id="tag-first-message-keywords"
                  value={editor.firstMessageKeywords}
                  disabled={!editor.firstMessageEnabled}
                  invalid={ruleError !== null}
                  placeholder="INTERESTED, RECHARGE"
                  onChange={(event) =>
                    setEditor({ ...editor, firstMessageKeywords: event.target.value })
                  }
                />
              </Field>
            </div>

            <div>
              <p className="mb-1.5 text-xs font-semibold text-text-secondary">Preview</p>
              <TagChip
                name={editor.name.trim() === "" ? "Tag name" : editor.name.trim()}
                color={colorError === null && editor.color.trim() !== "" ? editor.color.trim() : null}
              />
            </div>

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
                {saving ? "Saving…" : editor.tag ? "Save changes" : "Create tag"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}

      {confirmDelete ? (
        <Modal title={`Delete ${confirmDelete.name}?`} onClose={() => setConfirmDelete(null)}>
          <p className="text-sm text-text-secondary">
            {confirmDelete.usage_count > 0
              ? `This tag is applied to ${formatCount(confirmDelete.usage_count)} contact${
                  confirmDelete.usage_count === 1 ? "" : "s"
                }. Deleting it removes the tag from all of them.`
              : "This tag is not applied to any contact."}{" "}
            Deleting a tag cannot be undone.
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
              {remove.isPending ? "Deleting…" : "Delete tag"}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
