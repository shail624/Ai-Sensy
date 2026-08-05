import { Plus, Search, Tag as TagIcon } from "lucide-react";
import { useMemo, useState } from "react";

import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Field,
  FilterBar,
  Input,
  Modal,
  Pagination,
  Section,
  Select,
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
import { formatCount, formatDateTime } from "@/lib/format";

/** The list endpoint returns every tag at once, so paging is done here to keep the table readable. */
const PAGE_SIZE = 25;

interface EditorState {
  /** The tag being amended, or `null` when creating a new one. */
  tag: Tag | null;
  name: string;
  color: string;
  description: string;
}

function emptyEditor(): EditorState {
  return { tag: null, name: "", color: "", description: "" };
}

function editorFor(tag: Tag): EditorState {
  return {
    tag,
    name: tag.name,
    color: tag.color ?? "",
    description: tag.description ?? "",
  };
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
  const editorValid = !nameError && !colorError && !descriptionError;
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

  const newTagButton = canManage ? (
    <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => setEditor(emptyEditor())}>
      New tag
    </Button>
  ) : null;

  return (
    <Section
      title="Tags"
      description="The shared tag vocabulary for contacts and conversations. Renaming a tag updates it everywhere it is already applied."
      action={newTagButton}
    >
      <p className="mb-3 text-sm text-text-secondary">
        {all.length === 0
          ? "No tags exist yet."
          : `${formatCount(all.length)} tag${all.length === 1 ? "" : "s"} · ${formatCount(inUse)} in use`}
      </p>

      {remove.error ? (
        <div className="mb-3">
          <ErrorState message={apiErrorMessage(remove.error)} />
        </div>
      ) : null}

      {all.length > 0 ? (
        <div className="mb-3">
          <FilterBar label="Tag search and filters" contentClassName="w-full">
            <Input
              id="tags-search"
              type="search"
              value={search}
              onChange={(event) => narrow(() => setSearch(event.target.value))}
              placeholder="Search name or description…"
              aria-label="Search tags"
              leadingIcon={<Search aria-hidden className="h-4 w-4" />}
              containerClassName="min-w-0 flex-1 sm:min-w-[220px]"
            />
            <Select
              aria-label="Filter by usage"
              value={usage}
              onChange={(event) => narrow(() => setUsage(event.target.value as TagUsageFilter))}
              className="min-w-[10rem] !w-auto"
            >
              <option value="all">All tags</option>
              <option value="used">In use</option>
              <option value="unused">Unused</option>
            </Select>
          </FilterBar>
        </div>
      ) : null}

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
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">
                    Tag
                  </th>
                  <th scope="col" className="px-3 py-2">
                    Usage
                  </th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">
                    Last updated
                  </th>
                  {canManage ? (
                    <th scope="col" className="px-3 py-2 text-right">
                      Actions
                    </th>
                  ) : null}
                </tr>
              </thead>
              <tbody>
                {rows.map((tag) => (
                  <tr key={tag.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2 align-top">
                      <TagChip name={tag.name} color={tag.color} />
                      {tag.description ? (
                        <p className="mt-1 max-w-md text-xs text-text-secondary">
                          {tag.description}
                        </p>
                      ) : null}
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
                        <div className="flex flex-wrap justify-end gap-1">
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => setEditor(editorFor(tag))}
                          >
                            Edit
                          </Button>
                          <Button
                            variant="danger"
                            size="sm"
                            onClick={() => setConfirmDelete(tag)}
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
    </Section>
  );
}
