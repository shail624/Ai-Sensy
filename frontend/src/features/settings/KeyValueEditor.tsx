import { useMemo, useState } from "react";

import { EmptyState, ErrorState } from "@/components/ui";
import type { ValueDraft, ValueType } from "@/features/settings/types";
import {
  draftFromValue,
  parseValue,
  validateKey,
  VALUE_TYPE_LABELS,
  VALUE_TYPES,
} from "@/features/settings/types";
import { formatDateTime } from "@/lib/format";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50";

export interface KeyValueEntry {
  key: string;
  value: unknown;
  /** False for rows the API will not accept a write for — rendered read-only, with a reason. */
  editable: boolean;
  /** Shown beside the key when the row cannot be edited. */
  readOnlyReason?: string;
  /** The server withholds the value; nothing is rendered and nothing can be typed. */
  secret?: boolean;
  scope?: string;
  updatedAt?: string;
}

interface Props {
  entries: KeyValueEntry[];
  /** Called with only the changed keys — these APIs upsert, so sending untouched keys is noise. */
  onSave: (values: Record<string, unknown>) => void;
  canEdit: boolean;
  pending: boolean;
  error: unknown;
  /** Whether new keys may be added. These stores are schemaless, so a key is created by writing it. */
  allowAdd?: boolean;
  emptyTitle: string;
  emptyDescription: string;
  /** Rendered above the table — what this particular store is and who reads it. */
  note?: string;
}

/**
 * A key/value editor over one of the platform's schemaless configuration stores.
 *
 * All three of them — organization settings, the settings table, and user preferences — are
 * untyped `dict[str, Any]` blobs with no seeded keys and no catalog endpoint. There is no list of
 * known settings to render a form from, so the honest surface is the store itself: whatever keys
 * exist, with their stored types, and the ability to add one.
 *
 * Values are typed explicitly rather than guessed. The server infers the stored type from the JSON
 * it receives, so `"true"` and `true` are different stored values — asking for the type is what
 * stops an operator writing a string that reads like a boolean and behaves like neither.
 *
 * One implementation, used by every store, so a setting is edited the same way wherever it lives.
 */
export function KeyValueEditor({
  entries,
  onSave,
  canEdit,
  pending,
  error,
  allowAdd = false,
  emptyTitle,
  emptyDescription,
  note,
}: Props): JSX.Element {
  const [drafts, setDrafts] = useState<Record<string, ValueDraft>>({});
  const [adding, setAdding] = useState(false);
  const [newKey, setNewKey] = useState("");
  const [newDraft, setNewDraft] = useState<ValueDraft>({ type: "string", text: "" });
  const [showErrors, setShowErrors] = useState(false);

  const existingKeys = useMemo(() => entries.map((entry) => entry.key), [entries]);

  function draftFor(entry: KeyValueEntry): ValueDraft {
    return drafts[entry.key] ?? draftFromValue(entry.value);
  }

  function setDraft(key: string, next: ValueDraft): void {
    setDrafts((current) => ({ ...current, [key]: next }));
  }

  /** Only rows the operator actually touched, and only if they parse. */
  const changed = useMemo(() => {
    const values: Record<string, unknown> = {};
    const problems: Record<string, string> = {};
    for (const [key, draft] of Object.entries(drafts)) {
      const parsed = parseValue(draft);
      if (!parsed.ok) {
        problems[key] = parsed.error ?? "Invalid value";
        continue;
      }
      const original = entries.find((entry) => entry.key === key)?.value;
      if (JSON.stringify(parsed.value) !== JSON.stringify(original)) {
        values[key] = parsed.value;
      }
    }
    return { values, problems };
  }, [drafts, entries]);

  const keyProblem = adding ? validateKey(newKey, existingKeys) : null;
  const newParsed = parseValue(newDraft);
  const dirty = Object.keys(changed.values).length > 0;
  const blocked = Object.keys(changed.problems).length > 0;

  /**
   * A row that does not parse is not a saveable change, but it *is* a pending edit — so Save stays
   * enabled. Disabling it would leave an operator with a broken value, a dead button and no
   * explanation of either.
   */
  const hasPendingEdits = dirty || adding || blocked;

  function save(): void {
    setShowErrors(true);
    if (blocked) return;

    const payload = { ...changed.values };
    if (adding) {
      if (keyProblem || !newParsed.ok) return;
      payload[newKey.trim()] = newParsed.value;
    }
    if (Object.keys(payload).length === 0) return;

    onSave(payload);
    setDrafts({});
    setAdding(false);
    setNewKey("");
    setNewDraft({ type: "string", text: "" });
    setShowErrors(false);
  }

  function discard(): void {
    setDrafts({});
    setAdding(false);
    setNewKey("");
    setNewDraft({ type: "string", text: "" });
    setShowErrors(false);
  }

  if (entries.length === 0 && !adding) {
    return (
      <>
        {note ? <p className="mb-3 text-xs text-text-disabled">{note}</p> : null}
        <EmptyState title={emptyTitle} description={emptyDescription} />
        {canEdit && allowAdd ? (
          <div className="mt-3 flex justify-center">
            <button type="button" className={BUTTON_CLASS} onClick={() => setAdding(true)}>
              Add a setting
            </button>
          </div>
        ) : null}
      </>
    );
  }

  return (
    <>
      {note ? <p className="mb-3 text-xs text-text-disabled">{note}</p> : null}

      <div className="overflow-x-auto rounded-md border border-border">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
            <tr>
              <th scope="col" className="px-3 py-2">Key</th>
              <th scope="col" className="px-3 py-2">Type</th>
              <th scope="col" className="px-3 py-2">Value</th>
              <th scope="col" className="hidden px-3 py-2 lg:table-cell">Last updated</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => {
              const draft = draftFor(entry);
              const problem = showErrors ? changed.problems[entry.key] : undefined;
              const writable = canEdit && entry.editable && !entry.secret;

              return (
                <tr key={entry.key} className="border-b border-border last:border-0">
                  <td className="px-3 py-2 align-top">
                    <p className="break-all font-mono text-xs text-text-primary">{entry.key}</p>
                    {entry.scope ? (
                      <p className="text-xs text-text-disabled">{entry.scope}</p>
                    ) : null}
                    {!writable && entry.readOnlyReason ? (
                      <p className="mt-0.5 max-w-xs text-xs text-text-disabled">
                        {entry.readOnlyReason}
                      </p>
                    ) : null}
                  </td>

                  <td className="px-3 py-2 align-top">
                    {writable ? (
                      <select
                        aria-label={`Type of ${entry.key}`}
                        value={draft.type}
                        onChange={(event) =>
                          setDraft(entry.key, {
                            ...draft,
                            type: event.target.value as ValueType,
                          })
                        }
                        className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
                      >
                        {VALUE_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {VALUE_TYPE_LABELS[type]}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs text-text-secondary">
                        {VALUE_TYPE_LABELS[draft.type]}
                      </span>
                    )}
                  </td>

                  <td className="px-3 py-2 align-top">
                    {entry.secret ? (
                      <span className="text-xs text-text-disabled">
                        Hidden — the server never returns secret values
                      </span>
                    ) : writable ? (
                      <ValueInput
                        id={`setting-${entry.key}`}
                        label={entry.key}
                        draft={draft}
                        onChange={(next) => setDraft(entry.key, next)}
                      />
                    ) : (
                      <ReadOnlyValue draft={draft} />
                    )}
                    {problem ? <p className="mt-1 text-xs text-danger">{problem}</p> : null}
                  </td>

                  <td className="hidden px-3 py-2 align-top text-xs text-text-secondary lg:table-cell">
                    {entry.updatedAt ? formatDateTime(entry.updatedAt) : "—"}
                  </td>
                </tr>
              );
            })}

            {adding ? (
              <tr className="border-b border-border last:border-0 bg-surface-2/40">
                <td className="px-3 py-2 align-top">
                  <label htmlFor="new-setting-key" className="sr-only">
                    New setting key
                  </label>
                  <input
                    id="new-setting-key"
                    value={newKey}
                    onChange={(event) => setNewKey(event.target.value)}
                    placeholder="messaging.default_locale"
                    className={`${FIELD_CLASS} font-mono text-xs`}
                  />
                  {showErrors && keyProblem ? (
                    <p className="mt-1 text-xs text-danger">{keyProblem}</p>
                  ) : null}
                </td>
                <td className="px-3 py-2 align-top">
                  <select
                    aria-label="Type of the new setting"
                    value={newDraft.type}
                    onChange={(event) =>
                      setNewDraft({ ...newDraft, type: event.target.value as ValueType })
                    }
                    className="rounded-md border border-border bg-surface px-2 py-1 text-xs text-text-primary"
                  >
                    {VALUE_TYPES.map((type) => (
                      <option key={type} value={type}>
                        {VALUE_TYPE_LABELS[type]}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="px-3 py-2 align-top">
                  <ValueInput
                    id="new-setting-value"
                    label="the new setting"
                    draft={newDraft}
                    onChange={setNewDraft}
                  />
                  {showErrors && !newParsed.ok ? (
                    <p className="mt-1 text-xs text-danger">{newParsed.error}</p>
                  ) : null}
                </td>
                <td className="hidden px-3 py-2 lg:table-cell" />
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {error ? (
        <div className="mt-3">
          <ErrorState message={String((error as { detail?: string })?.detail ?? error)} />
        </div>
      ) : null}

      {canEdit ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
          {allowAdd && !adding ? (
            <button type="button" className={BUTTON_CLASS} onClick={() => setAdding(true)}>
              Add a setting
            </button>
          ) : (
            <span />
          )}

          <div className="flex flex-wrap items-center gap-2">
            {hasPendingEdits ? (
              <button type="button" className={BUTTON_CLASS} onClick={discard} disabled={pending}>
                Discard changes
              </button>
            ) : null}
            <button
              type="button"
              onClick={save}
              disabled={pending || !hasPendingEdits}
              className="rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg disabled:opacity-50"
            >
              {pending
                ? "Saving…"
                : dirty
                  ? `Save ${Object.keys(changed.values).length + (adding ? 1 : 0)} change${
                      Object.keys(changed.values).length + (adding ? 1 : 0) === 1 ? "" : "s"
                    }`
                  : "Save"}
            </button>
          </div>
        </div>
      ) : null}
    </>
  );
}

/** The control for one value, matched to its declared type. */
function ValueInput({
  id,
  label,
  draft,
  onChange,
}: {
  id: string;
  label: string;
  draft: ValueDraft;
  onChange: (next: ValueDraft) => void;
}): JSX.Element {
  if (draft.type === "boolean") {
    return (
      <>
        <label htmlFor={id} className="sr-only">
          Value of {label}
        </label>
        <select
          id={id}
          value={draft.text}
          onChange={(event) => onChange({ ...draft, text: event.target.value })}
          className={FIELD_CLASS}
        >
          <option value="true">true</option>
          <option value="false">false</option>
        </select>
      </>
    );
  }

  if (draft.type === "json") {
    return (
      <>
        <label htmlFor={id} className="sr-only">
          Value of {label}
        </label>
        <textarea
          id={id}
          rows={3}
          value={draft.text}
          onChange={(event) => onChange({ ...draft, text: event.target.value })}
          className={`${FIELD_CLASS} font-mono text-xs`}
        />
      </>
    );
  }

  return (
    <>
      <label htmlFor={id} className="sr-only">
        Value of {label}
      </label>
      <input
        id={id}
        type={draft.type === "number" ? "number" : "text"}
        value={draft.text}
        onChange={(event) => onChange({ ...draft, text: event.target.value })}
        className={FIELD_CLASS}
      />
    </>
  );
}

function ReadOnlyValue({ draft }: { draft: ValueDraft }): JSX.Element {
  if (draft.type === "json") {
    return (
      <pre className="max-w-md overflow-x-auto rounded border border-border bg-surface-2 p-2 text-xs text-text-primary">
        {draft.text}
      </pre>
    );
  }
  return <span className="break-all font-mono text-xs text-text-primary">{draft.text || "—"}</span>;
}
