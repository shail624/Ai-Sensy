import { ListPlus, Plus, Search } from "lucide-react";
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
import { formatDateTime } from "@/lib/format";

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

    if (editor.definition) {
      update.mutate(
        { id: editor.definition.id, body: { label, enum_values: enumValues, is_indexed: isIndexed, is_pii: isPii } },
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
    <Button leftIcon={<Plus className="h-4 w-4" />} onClick={() => openEditor(emptyEditor())}>
      New attribute
    </Button>
  ) : null;

  return (
    <Section
      title="User Attributes"
      description="Typed custom fields available on every contact, campaign audience and segment."
      action={newAttributeButton}
    >
      <p className="mb-3 text-sm text-text-secondary">
        {all.length === 0
          ? "No user attributes exist yet."
          : `${all.length} attribute${all.length === 1 ? "" : "s"}`}
      </p>

      {all.length > 0 ? (
        <div className="mb-3">
          <FilterBar label="User attribute search and filters" contentClassName="w-full">
            <Input
              id="user-attributes-search"
              type="search"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Search key name or label…"
              aria-label="Search user attributes"
              leadingIcon={<Search aria-hidden className="h-4 w-4" />}
              containerClassName="min-w-0 flex-1 sm:min-w-[220px]"
            />
            <Select
              aria-label="Filter by type"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value as AttributeTypeFilter)}
              className="min-w-[10rem] !w-auto"
            >
              <option value="all">All types</option>
              {ATTRIBUTE_DATA_TYPES.map((type) => (
                <option key={type} value={type}>
                  {ATTRIBUTE_DATA_TYPE_LABELS[type]}
                </option>
              ))}
            </Select>
          </FilterBar>
        </div>
      ) : null}

      {all.length === 0 ? (
        <EmptyState
          icon={<ListPlus aria-hidden className="h-6 w-6" />}
          title="No user attributes yet"
          description={
            canManage
              ? "Define the first typed field so it can be set on contacts and used in segments."
              : "Nobody has defined a user attribute yet. You need the contacts write permission to add one."
          }
          action={newAttributeButton}
        />
      ) : matching.length === 0 ? (
        <EmptyState
          title="No user attributes match"
          description="No attribute matches this search and filter."
          action={
            <Button
              variant="secondary"
              onClick={() => {
                setSearch("");
                setTypeFilter("all");
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
                <th scope="col" className="px-3 py-2">Key name</th>
                <th scope="col" className="px-3 py-2">Label</th>
                <th scope="col" className="px-3 py-2">Type</th>
                <th scope="col" className="hidden px-3 py-2 md:table-cell">Indexed</th>
                <th scope="col" className="hidden px-3 py-2 md:table-cell">PII</th>
                <th scope="col" className="hidden px-3 py-2 lg:table-cell">Updated At</th>
                {canManage ? (
                  <th scope="col" className="px-3 py-2 text-right">Actions</th>
                ) : null}
              </tr>
            </thead>
            <tbody>
              {matching.map((definition) => (
                <tr key={definition.id} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 align-top font-mono text-xs text-text-primary">
                    {definition.key_name}
                  </td>
                  <td className="px-3 py-2 align-top text-text-primary">{definition.label}</td>
                  <td className="px-3 py-2 align-top">
                    <Badge tone="neutral">
                      {ATTRIBUTE_DATA_TYPE_LABELS[definition.data_type as AttributeDataType] ??
                        definition.data_type}
                    </Badge>
                  </td>
                  <td className="hidden px-3 py-2 align-top md:table-cell">
                    {definition.is_indexed ? (
                      <Badge tone="accent" title="Mirrored for fast contact-list and campaign rendering.">
                        Indexed
                      </Badge>
                    ) : (
                      <span className="text-xs text-text-disabled">—</span>
                    )}
                  </td>
                  <td className="hidden px-3 py-2 align-top md:table-cell">
                    {definition.is_pii ? (
                      <Badge tone="warning" title="Flagged as personally identifiable information.">
                        PII
                      </Badge>
                    ) : (
                      <span className="text-xs text-text-disabled">—</span>
                    )}
                  </td>
                  <td className="hidden px-3 py-2 align-top text-xs text-text-secondary lg:table-cell">
                    {formatDateTime(definition.updated_at)}
                  </td>
                  {canManage ? (
                    <td className="px-3 py-2 align-top">
                      <div className="flex flex-wrap justify-end gap-1">
                        <Button
                          variant="secondary"
                          size="sm"
                          aria-label={`Edit ${definition.label}`}
                          onClick={() => openEditor(editorFor(definition))}
                        >
                          Edit
                        </Button>
                        <Button
                          variant="danger"
                          size="sm"
                          aria-label={`Delete ${definition.label}`}
                          onClick={() => openDeleteConfirm(definition)}
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
          Read-only — changing user attributes needs the contacts write permission.
        </p>
      ) : null}

      {editor ? (
        <Modal
          title={editor.definition ? `Edit ${editor.definition.label}` : "New user attribute"}
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
    </Section>
  );
}
