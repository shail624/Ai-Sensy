import { useState } from "react";

import { EmptyState, ErrorState, Section, Spinner, TagChip } from "@/components/ui";
import {
  apiErrorMessage,
  useAddContactTags,
  useRemoveContactTag,
  useTags,
} from "@/features/customer-profile/api";
import type { Contact } from "@/features/customer-profile/types";

/** Tags: view current tags and add/remove them (POST/DELETE /contacts/{id}/tags). */
export function TagsSection({ contact }: { contact: Contact }): JSX.Element {
  const available = useTags();
  const addTags = useAddContactTags(contact.id);
  const removeTag = useRemoveContactTag(contact.id);
  const [selected, setSelected] = useState("");

  const applied = new Set(contact.tags.map((tag) => tag.id));
  const options = (available.data ?? []).filter((tag) => !applied.has(tag.id));

  return (
    <Section title="Tags">
      {contact.tags.length === 0 ? (
        <EmptyState title="No tags yet" />
      ) : (
        <ul className="flex flex-wrap gap-2">
          {contact.tags.map((tag) => (
            <li key={tag.id}>
              <TagChip
                name={tag.name}
                color={tag.color}
                removing={removeTag.isPending}
                onRemove={() => removeTag.mutate(tag.id)}
              />
            </li>
          ))}
        </ul>
      )}

      <form
        className="mt-3 flex items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (!selected) return;
          addTags.mutate([selected], { onSuccess: () => setSelected("") });
        }}
      >
        <label className="sr-only" htmlFor="add-tag">
          Add a tag
        </label>
        <select
          id="add-tag"
          value={selected}
          onChange={(event) => setSelected(event.target.value)}
          disabled={available.isLoading || options.length === 0}
          className="flex-1 rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary"
        >
          <option value="">{options.length === 0 ? "No more tags to add" : "Select a tag…"}</option>
          {options.map((tag) => (
            <option key={tag.id} value={tag.id}>
              {tag.name}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={!selected || addTags.isPending}
          className="rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50"
        >
          {addTags.isPending ? <Spinner label="Adding…" /> : "Add"}
        </button>
      </form>

      {available.isError ? (
        <div className="mt-2">
          <ErrorState message={apiErrorMessage(available.error)} />
        </div>
      ) : null}
      {addTags.isError ? (
        <div className="mt-2">
          <ErrorState message={apiErrorMessage(addTags.error)} />
        </div>
      ) : null}
      {removeTag.isError ? (
        <div className="mt-2">
          <ErrorState message={apiErrorMessage(removeTag.error)} />
        </div>
      ) : null}
    </Section>
  );
}
