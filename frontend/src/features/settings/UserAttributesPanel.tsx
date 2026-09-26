import { ListPlus, Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";

import {
  Badge,
  Button,
  DefinitionRow,
  EmptyState,
  ErrorState,
  Field,
  Input,
  Modal,
  Select,
  Spinner,
} from "@/components/ui";
import {
  apiErrorMessage,
  useAttributeDefinitions,
  useCreateAttributeDefinition,
  useDeleteAttributeDefinition,
  useHasPermission,
  useUpdateAttributeDefinition,
} from "@/features/settings/api";
import type { AttributeDefinition, AttributeDataType, AttributeTypeFilter } from "@/features/settings/types";
import {
  ATTRIBUTE_DATA_TYPES,
  ATTRIBUTE_DATA_TYPE_LABELS,
  MAX_ATTRIBUTE_KEY_NAME,
  MAX_ATTRIBUTE_LABEL,
  matchesAttributeFilter,
  parseEnumValues,
  validateAttributeEnumValues,
  validateAttributeKeyName,
  validateAttributeLabel,
} from "@/features/settings/types";
import { MANAGE_CARD, MANAGE_FIELD, MANAGE_OUTLINE, Toggle } from "@/features/settings/managePrimitives";
import { formatDateTime } from "@/lib/format";

/** The reference row action: a 30px round icon button in the brand teal. */
const ROW_ICON =
  "flex h-[30px] w-[30px] items-center justify-center rounded-full text-[var(--color-nav-bg)] transition-colors duration-150 hover:bg-[#ebf5f3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-accent";

interface EditorState {
  /** The definition being amended, or `null` when creating a new one. */
  definition: AttributeDefinition | null;
  keyName: string;
  label: string;
  dataType: AttributeDataType;
  /** Comma-separated as typed; parsed with `parseEnumValues` on submit. */
  enumValuesText: string;
  isIndexed: boolean;
  isPii: boolean;
  isRequired: boolean;
  isActive: boolean;
}

function emptyEditor(): EditorState {
  return {
    definition: null,
    keyName: "",
    label: "",
    dataType: "string",
    enumValuesText: "",
    isIndexed: false,
    isPii: false,
    isRequired: false,
    isActive: true,
  };
}

function editorFor(definition: AttributeDefinition): EditorState {
  return {
    definition,
    keyName: definition.key_name,
    label: definition.label,
    dataType: definition.data_type as AttributeDataType,
    enumValuesText: (definition.enum_values ?? []).join(", "),
    isIndexed: definition.is_indexed,
    isPii: definition.is_pii,
    isRequired: definition.is_required,
    isActive: definition.is_active,
  };
}

/**
 * User attribute administration (Doc 04 §14.4).
 *
 * These definitions were reachable only through the API before this screen existed: contacts,
 * campaign audience rules and segment predicates all read the same `/custom-attributes` list, but
 * nothing could add to it, so a fresh organization had no typed fields to attach anywhere.
 *
 * `key_name` and `data_type` are fixed forever once a definition is created — changing either would
 * invalidate every stored value's column and any segment rule already referencing the key — so the
 * edit dialog shows both as read-only facts rather than controls.
 */
export function UserAttributesPanel(): JSX.Element {
  const canManage = useHasPermission("contacts:write");
  const definitions = useAttributeDefinitions();
  const create = useCreateAttributeDefinition();
  const update = useUpdateAttributeDefinition();
  const remove = useDeleteAttributeDefinition();

  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<AttributeTypeFilter>("all");
  const [editor, setEditor] = useState<EditorState | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<AttributeDefinition | null>(null);

  const all = [...(definitions.data ?? [])].sort((a, b) => a.key_name.localeCompare(b.key_name));
  const matching = all.filter((definition) => matchesAttributeFilter(definition, search, typeFilter));

  const keyNameError = editor ? validateAttributeKeyName(editor.keyName) : null;
  const labelError = editor ? validateAttributeLabel(editor.label) : null;
  const enumValuesError = editor
    ? validateAttributeEnumValues(editor.dataType, editor.enumValuesText)
    : null;
  const editorValid = !keyNameError && !labelError && !enumValuesError;
  const saving = create.isPending || update.isPending;
  const isEnum = editor?.dataType === "enum";

  function openEditor(next: EditorState): void {
    // A previous failure must not resurface as a stale error the moment a different dialog opens.
    create.reset();
    update.reset();
    setEditor(next);
  }

  function openDeleteConfirm(definition: AttributeDefinition): void {
    remove.reset();
    setConfirmDelete(definition);
  }

  function submitEditor(): void {
    if (!editor || !editorValid) return;

    const label = editor.label.trim();
    const enumValues = isEnum ? parseEnumValues(editor.enumValuesText) : null;
    const isIndexed = editor.isIndexed;
    const isPii = editor.isPii;
    const isRequired = editor.isRequired;
    const isActive = editor.isActive;

    if (editor.definition) {
      update.mutate(
        {
          id: editor.definition.id,
          body: {
            label,
            enum_values: enumValues,
            is_indexed: isIndexed,
            is_pii: isPii,
            is_required: isRequired,
            is_active: isActive,
          },
        },
        { onSuccess: () => setEditor(null) },
      );
    } else {
      create.mutate(
        {
          key_name: editor.keyName.trim(),
          label,
          data_type: editor.dataType,
          enum_values: enumValues,
          is_indexed: isIndexed,
          is_pii: isPii,
          is_required: isRequired,
          is_active: isActive,
        },
        { onSuccess: () => setEditor(null) },
      );
    }
  }

  if (definitions.isLoading) return <Spinner label="Loading user attributes…" />;

  if (definitions.isError) {
    return (
      <ErrorState
        message={apiErrorMessage(definitions.error)}
        onRetry={() => void definitions.refetch()}
      />
    );
  }

  const newAttributeButton = canManage ? (
    <button type="button" onClick={() => openEditor(emptyEditor())} className={`${MANAGE_OUTLINE} !h-[37px] px-4 text-sm`}>
      <Plus aria-hidden className="h-4 w-4" /> Add attribute
    </button>
  ) : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex h-[42px] w-full max-w-[454px] items-center gap-2 rounded-[8px] bg-surface px-[15px] shadow-[0_1px_2px_rgba(0,0,0,0.04)]">
          <Search aria-hidden className="h-4 w-4 shrink-0 text-black/40" />
          <input
            id="user-attributes-search"
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search by attributes name"
            aria-label="Search user attributes"
            className="h-full min-w-0 flex-1 bg-transparent text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus:outline-none dark:text-text-primary"
          />
        </div>
        <select
          aria-label="Filter by type"
          value={typeFilter}
          onChange={(event) => setTypeFilter(event.target.value as AttributeTypeFilter)}
          className={`${MANAGE_FIELD} h-10 w-[141px] pr-7`}
        >
          <option value="all">All</option>
          {ATTRIBUTE_DATA_TYPES.map((type) => (
            <option key={type} value={type}>
              {ATTRIBUTE_DATA_TYPE_LABELS[type]}
            </option>
          ))}
        </select>
        {newAttributeButton}
        <p className="ml-auto text-sm text-[#6e6e6e] dark:text-text-secondary">
          {all.length === 0 ? "No user attributes exist yet." : `${all.length} attribute${all.length === 1 ? "" : "s"}`}
        </p>
      </div>

      {all.length === 0 ? (
        <div className={`${MANAGE_CARD} py-6`}>
          <EmptyState
            icon={<ListPlus aria-hidden className="h-6 w-6" />}
            title="No user attributes yet"
            description={
              canManage
                ? "Define the first typed field so it can be set on contacts and used in segments."
                : "Nobody has defined a user attribute yet. You need the contacts write permission to add one."
            }
          />
        </div>
      ) : matching.length === 0 ? (
        <div className={`${MANAGE_CARD} py-6`}>
          <EmptyState
            title="No user attributes match"
            description="No attribute matches this search and filter."
            action={
              <button type="button" className={MANAGE_OUTLINE} onClick={() => { setSearch(""); setTypeFilter("all"); }}>
                Clear filters
              </button>
            }
          />
        </div>
      ) : (
        <div className="overflow-x-auto rounded-[8px] bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-[#f0f0f0] text-sm text-[var(--color-nav-bg)] dark:border-border dark:text-accent">
              <tr className="h-[55px]">
                <th scope="col" className="pl-8 pr-3 font-normal">Name*</th>
                <th scope="col" className="px-3 font-normal">Key</th>
                <th scope="col" className="px-3 font-normal">Type</th>
                <th scope="col" className="hidden px-3 font-normal lg:table-cell">Updated</th>
                <th scope="col" className="px-3 font-normal">Status</th>
                {canManage ? <th scope="col" className="pl-3 pr-8 text-right font-normal">Action</th> : null}
              </tr>
            </thead>
            <tbody>
              {matching.map((definition) => (
                <tr key={definition.id} className="border-b border-[#f0f0f0] last:border-0 dark:border-border">
                  <td className="py-4 pl-8 pr-3 align-middle">
                    <span className="inline-flex min-h-[42px] min-w-[200px] items-center rounded-[8px] bg-[#f0f0f0] px-[15px] text-sm text-[#4a4a4a] dark:bg-surface-2 dark:text-text-primary">
                      {definition.label}
                    </span>
                    <span className="mt-1.5 flex flex-wrap gap-1">
                      {definition.is_indexed ? (
                        <Badge tone="accent" title="Mirrored for fast contact-list and campaign rendering.">Indexed</Badge>
                      ) : null}
                      {definition.is_pii ? (
                        <Badge tone="warning" title="Flagged as personally identifiable information.">PII</Badge>
                      ) : null}
                      {definition.is_required ? (
                        <Badge tone="info" title="Once set, this value cannot be cleared.">Required</Badge>
                      ) : null}
                      {!definition.is_active ? (
                        <Badge tone="neutral" title="Takes no new values. What was recorded stays readable.">Retired</Badge>
                      ) : null}
                    </span>
                  </td>
                  <td className="px-3 align-middle font-mono text-xs text-[#4a4a4a] dark:text-text-secondary">{definition.key_name}</td>
                  <td className="px-3 align-middle text-[#4a4a4a] dark:text-text-secondary">
                    {ATTRIBUTE_DATA_TYPE_LABELS[definition.data_type as AttributeDataType] ?? definition.data_type}
                  </td>
                  <td className="hidden px-3 align-middle text-xs text-[#6e6e6e] lg:table-cell">{formatDateTime(definition.updated_at)}</td>
                  <td className="px-3 align-middle">
                    <Toggle
                      checked={definition.is_active}
                      disabled={!canManage || update.isPending}
                      label={`${definition.label} active`}
                      onChange={(isActive) => update.mutate({ id: definition.id, body: { is_active: isActive } })}
                    />
                  </td>
                  {canManage ? (
                    <td className="pl-3 pr-8 align-middle">
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          aria-label={`Edit ${definition.label}`}
                          title="Edit attribute"
                          onClick={() => openEditor(editorFor(definition))}
                          className={ROW_ICON}
                        >
                          <Pencil aria-hidden className="h-[18px] w-[18px]" />
                        </button>
                        <button
                          type="button"
                          aria-label={`Delete ${definition.label}`}
                          title="Delete attribute"
                          onClick={() => openDeleteConfirm(definition)}
                          className={`${ROW_ICON} hover:!bg-danger-soft hover:!text-danger`}
                        >
                          <Trash2 aria-hidden className="h-[18px] w-[18px]" />
                        </button>
                      </div>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {update.error && !editor ? <ErrorState message={apiErrorMessage(update.error)} /> : null}

      {!canManage ? (
        <p className="text-xs text-text-disabled">
          Read-only — changing user attributes needs the contacts write permission.
        </p>
      ) : null}

      {editor ? (
        <Modal
          title={editor.definition ? `Edit ${editor.definition.label}` : "Add user attribute"}
          onClose={() => setEditor(null)}
        >
          <form
            onSubmit={(event) => {
              event.preventDefault();
              submitEditor();
            }}
            className="space-y-4"
          >
            {editor.definition ? (
              <dl>
                <DefinitionRow label="Key name">
                  <span className="font-mono text-xs">{editor.definition.key_name}</span>
                </DefinitionRow>
                <DefinitionRow label="Type">
                  {ATTRIBUTE_DATA_TYPE_LABELS[editor.definition.data_type as AttributeDataType] ??
                    editor.definition.data_type}
                </DefinitionRow>
              </dl>
            ) : (
              <>
                <Field
                  htmlFor="attribute-key-name"
                  label="Key name"
                  error={editor.keyName === "" ? null : keyNameError}
                  description={`Up to ${MAX_ATTRIBUTE_KEY_NAME} characters. Cannot be changed after creation.`}
                >
                  <Input
                    id="attribute-key-name"
                    value={editor.keyName}
                    maxLength={MAX_ATTRIBUTE_KEY_NAME}
                    invalid={editor.keyName !== "" && keyNameError !== null}
                    onChange={(event) => setEditor({ ...editor, keyName: event.target.value })}
                  />
                </Field>

                <Field
                  htmlFor="attribute-data-type"
                  label="Type"
                  description="Determines how values are stored and validated. Cannot be changed after creation."
                >
                  <Select
                    id="attribute-data-type"
                    value={editor.dataType}
                    onChange={(event) =>
                      setEditor({ ...editor, dataType: event.target.value as AttributeDataType })
                    }
                  >
                    {ATTRIBUTE_DATA_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {ATTRIBUTE_DATA_TYPE_LABELS[type]}
                      </option>
                    ))}
                  </Select>
                </Field>
              </>
            )}

            <Field
              htmlFor="attribute-label"
              label="Label"
              error={editor.label === "" ? null : labelError}
              description={`Up to ${MAX_ATTRIBUTE_LABEL} characters. Shown wherever this attribute appears.`}
            >
              <Input
                id="attribute-label"
                value={editor.label}
                maxLength={MAX_ATTRIBUTE_LABEL}
                invalid={editor.label !== "" && labelError !== null}
                onChange={(event) => setEditor({ ...editor, label: event.target.value })}
              />
            </Field>

            {isEnum ? (
              <Field
                htmlFor="attribute-enum-values"
                label="Choices"
                error={editor.enumValuesText === "" ? null : enumValuesError}
                description="Comma-separated. At least one choice is required."
              >
                <Input
                  id="attribute-enum-values"
                  value={editor.enumValuesText}
                  placeholder="gold, silver, bronze"
                  invalid={editor.enumValuesText !== "" && enumValuesError !== null}
                  onChange={(event) => setEditor({ ...editor, enumValuesText: event.target.value })}
                />
              </Field>
            ) : null}

            <label className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={editor.isIndexed}
                onChange={(event) => setEditor({ ...editor, isIndexed: event.target.checked })}
                className="mt-0.5"
              />
              <span>
                <span className="block text-text-primary">Indexed</span>
                <span className="block text-xs text-text-secondary">
                  Mirrors this attribute&rsquo;s value for fast contact-list and campaign rendering.
                </span>
              </span>
            </label>

            <label className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={editor.isPii}
                onChange={(event) => setEditor({ ...editor, isPii: event.target.checked })}
                className="mt-0.5"
              />
              <span>
                <span className="block text-text-primary">Personally identifiable information</span>
                <span className="block text-xs text-text-secondary">
                  Flags this attribute as PII. Not yet enforced elsewhere in the product.
                </span>
              </span>
            </label>

            <label className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={editor.isRequired}
                onChange={(event) => setEditor({ ...editor, isRequired: event.target.checked })}
                className="mt-0.5"
              />
              <span>
                <span className="block text-text-primary">Required</span>
                <span className="block text-xs text-text-secondary">
                  Once set, this value cannot be cleared. It does not force every update to carry
                  it: attributes are saved a few at a time, so demanding the field on every write
                  would block ordinary edits and every import.
                </span>
              </span>
            </label>

            <label className="flex cursor-pointer items-start gap-2 text-sm">
              <input
                type="checkbox"
                checked={!editor.isActive}
                onChange={(event) => setEditor({ ...editor, isActive: !event.target.checked })}
                className="mt-0.5"
              />
              <span>
                <span className="block text-text-primary">Retired</span>
                <span className="block text-xs text-text-secondary">
                  Stops accepting new values. What was already recorded stays readable and can
                  still be cleared, so a field can be wound down instead of deleted out from under
                  the contacts that carry it.
                </span>
              </span>
            </label>

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
                {saving ? "Saving…" : editor.definition ? "Save changes" : "Create attribute"}
              </Button>
            </div>
          </form>
        </Modal>
      ) : null}

      {confirmDelete ? (
        <Modal title={`Delete ${confirmDelete.label}?`} onClose={() => setConfirmDelete(null)}>
          <p className="text-sm text-text-secondary">
            Deleting <span className="font-medium text-text-primary">{confirmDelete.label}</span> removes
            this attribute and its stored value from every contact that has one. This cannot be undone.
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
              {remove.isPending ? "Deleting…" : "Delete attribute"}
            </Button>
          </div>
        </Modal>
      ) : null}
    </div>
  );
}
