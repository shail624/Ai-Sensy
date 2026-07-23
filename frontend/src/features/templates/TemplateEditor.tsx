import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useCreateTemplate,
  useUpdateTemplate,
  useWabas,
} from "@/features/templates/api";
import type { ButtonDraft, ButtonType, HeaderFormat, TemplateDraft } from "@/features/templates/components";
import {
  analyzeVariables,
  blankButton,
  blankDraft,
  BUTTON_TYPE_LABELS,
  BUTTON_TYPES,
  HEADER_FORMAT_LABELS,
  HEADER_FORMATS,
  MAX_BODY_CHARS,
  MAX_BUTTONS,
  MAX_FOOTER_CHARS,
  MAX_HEADER_CHARS,
  MEDIA_FORMATS,
} from "@/features/templates/components";
import { TemplateBubble } from "@/features/templates/TemplateBubble";
import { toCreateRequest, toUpdateRequest, validateDraft } from "@/features/templates/templateForm";
import type { FieldErrors } from "@/features/templates/templateForm";
import { VariableInspector } from "@/features/templates/VariableInspector";
import type { Category, Template } from "@/features/templates/types";
import { CATEGORIES, CATEGORY_LABELS } from "@/features/templates/types";

const FIELD_CLASS =
  "w-full rounded-md border border-border bg-surface px-2 py-1 text-sm text-text-primary";
const LABEL_CLASS = "text-xs font-medium text-text-secondary";
const BUTTON_CLASS = "rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover disabled:opacity-50";
const PRIMARY_CLASS = "rounded-md bg-accent px-3 py-1.5 text-sm text-accent-fg disabled:opacity-50";

interface Props {
  /** Absent → create a new template; present → edit that template's definition. */
  template?: Template;
  /** Prefilled values for a clone — a new template that starts from an existing one. */
  initialDraft?: TemplateDraft;
}

/**
 * The template builder (Doc 05 B5.2 — split editor + live preview). One component for create,
 * clone and edit.
 *
 * Create posts the whole definition and, unless held as a draft, submits it to Meta in the same
 * call. Edit sends the category and components with `row_version`, so a concurrent change surfaces
 * as the server's conflict rather than silently overwriting; name, language and WABA are fixed
 * because the contract does not accept them — they identify the template.
 *
 * Validation mirrors the server's rules so a rejection loop is avoided before it starts; the server
 * re-checks everything and its 422 is rendered verbatim.
 */
export function TemplateEditor({ template, initialDraft }: Props): JSX.Element {
  const navigate = useNavigate();
  const editing = template !== undefined;

  const [draft, setDraft] = useState<TemplateDraft>(initialDraft ?? blankDraft);
  const [showErrors, setShowErrors] = useState(false);

  const wabas = useWabas(!editing);
  const create = useCreateTemplate();
  const update = useUpdateTemplate();

  const errors: FieldErrors = useMemo(
    () => validateDraft(draft, { creating: !editing }),
    [draft, editing],
  );
  const analysis = useMemo(
    () => analyzeVariables(draft.header_format === "text" ? draft.header_text : "", draft.body_text),
    [draft.header_format, draft.header_text, draft.body_text],
  );

  const pending = create.isPending || update.isPending;
  const submitError = create.error ?? update.error;
  const visible = showErrors ? errors : {};

  function set<K extends keyof TemplateDraft>(key: K, value: TemplateDraft[K]): void {
    setDraft((current) => ({ ...current, [key]: value }));
  }

  function setButton(index: number, patch: Partial<ButtonDraft>): void {
    setDraft((current) => ({
      ...current,
      buttons: current.buttons.map((button, position) =>
        position === index ? { ...button, ...patch } : button,
      ),
    }));
  }

  function submit(withSubmission: boolean): void {
    setShowErrors(true);
    if (Object.keys(errors).length > 0) return;

    if (editing) {
      update.mutate(
        { templateId: template.id, body: toUpdateRequest(draft, template, withSubmission) },
        { onSuccess: (saved) => navigate(`/templates/${saved.id}`) },
      );
      return;
    }
    create.mutate(toCreateRequest(draft, withSubmission), {
      onSuccess: (created) => navigate(`/templates/${created.id}`),
    });
  }

  if (!editing && wabas.isLoading) return <Spinner label="Loading accounts…" />;

  const mediaFormat = MEDIA_FORMATS.includes(draft.header_format) ? draft.header_format : null;

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      {/* --- Editor ------------------------------------------------------------------------- */}
      <div className="space-y-4">
        <Section title="Identity">
          {editing ? (
            <p className="mb-3 text-xs text-text-disabled">
              Name, language and account identify the template and cannot change. Clone it instead
              to start a new one.
            </p>
          ) : null}

          <div className="space-y-3">
            {!editing ? (
              <div>
                <label htmlFor="template-waba" className={LABEL_CLASS}>
                  WhatsApp Business Account
                </label>
                <select
                  id="template-waba"
                  value={draft.waba_id}
                  onChange={(event) => set("waba_id", event.target.value)}
                  className={FIELD_CLASS}
                >
                  <option value="">Choose an account…</option>
                  {(wabas.data ?? []).map((waba) => (
                    <option key={waba.id} value={waba.id}>
                      {waba.business_name}
                    </option>
                  ))}
                </select>
                {visible.waba_id ? <p className="text-xs text-danger">{visible.waba_id}</p> : null}
                {(wabas.data ?? []).length === 0 ? (
                  <p className="mt-1 text-xs text-text-disabled">
                    No WhatsApp Business Accounts are connected yet.
                  </p>
                ) : null}
              </div>
            ) : null}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label htmlFor="template-name" className={LABEL_CLASS}>
                  Name
                </label>
                <input
                  id="template-name"
                  value={draft.name}
                  disabled={editing}
                  onChange={(event) => set("name", event.target.value)}
                  placeholder="order_update"
                  className={`${FIELD_CLASS} font-mono disabled:opacity-60`}
                />
                {visible.name ? <p className="text-xs text-danger">{visible.name}</p> : null}
              </div>
              <div>
                <label htmlFor="template-language" className={LABEL_CLASS}>
                  Language
                </label>
                <input
                  id="template-language"
                  value={draft.language}
                  disabled={editing}
                  onChange={(event) => set("language", event.target.value)}
                  placeholder="en_US"
                  className={`${FIELD_CLASS} font-mono disabled:opacity-60`}
                />
                {visible.language ? <p className="text-xs text-danger">{visible.language}</p> : null}
              </div>
            </div>

            <div>
              <label htmlFor="template-category" className={LABEL_CLASS}>
                Category
              </label>
              <select
                id="template-category"
                value={draft.category}
                onChange={(event) => set("category", event.target.value as Category)}
                className={FIELD_CLASS}
              >
                {CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {CATEGORY_LABELS[category]}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-text-disabled">
                Meta prices and reviews by category, and may recategorise a template it disagrees
                with.
              </p>
            </div>
          </div>
        </Section>

        <Section title="Header">
          <div className="space-y-3">
            <div>
              <label htmlFor="template-header-format" className={LABEL_CLASS}>
                Header type
              </label>
              <select
                id="template-header-format"
                value={draft.header_format}
                onChange={(event) => set("header_format", event.target.value as HeaderFormat)}
                className={FIELD_CLASS}
              >
                {HEADER_FORMATS.map((format) => (
                  <option key={format} value={format}>
                    {HEADER_FORMAT_LABELS[format]}
                  </option>
                ))}
              </select>
            </div>

            {draft.header_format === "text" ? (
              <div>
                <label htmlFor="template-header-text" className={LABEL_CLASS}>
                  Header text
                </label>
                <input
                  id="template-header-text"
                  value={draft.header_text}
                  onChange={(event) => set("header_text", event.target.value)}
                  className={FIELD_CLASS}
                />
                <p className="mt-1 text-xs text-text-disabled">
                  {draft.header_text.length}/{MAX_HEADER_CHARS} characters · at most one variable
                </p>
                {visible.header_text ? (
                  <p className="text-xs text-danger">{visible.header_text}</p>
                ) : null}
              </div>
            ) : mediaFormat ? (
              <p className="text-xs text-text-disabled">
                A {mediaFormat} header carries a file, never text. The file itself is supplied per
                send, so nothing more is set here.
              </p>
            ) : null}
          </div>
        </Section>

        <Section title="Body">
          <label htmlFor="template-body" className="sr-only">
            Body text
          </label>
          <textarea
            id="template-body"
            rows={6}
            value={draft.body_text}
            onChange={(event) => set("body_text", event.target.value)}
            placeholder="Hi {{1}}, your order {{2}} is on its way."
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            {draft.body_text.length}/{MAX_BODY_CHARS} characters · use {"{{1}}"}, {"{{2}}"} … for
            variables, numbered from 1 with no gaps
          </p>
          {visible.body_text ? <p className="text-xs text-danger">{visible.body_text}</p> : null}
        </Section>

        <Section title="Footer">
          <label htmlFor="template-footer" className="sr-only">
            Footer text
          </label>
          <input
            id="template-footer"
            value={draft.footer_text}
            onChange={(event) => set("footer_text", event.target.value)}
            placeholder="Reply STOP to opt out"
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-xs text-text-disabled">
            {draft.footer_text.length}/{MAX_FOOTER_CHARS} characters · optional, and no variables
          </p>
          {visible.footer_text ? <p className="text-xs text-danger">{visible.footer_text}</p> : null}
        </Section>

        <Section
          title="Buttons"
          action={
            draft.buttons.length < MAX_BUTTONS ? (
              <button
                type="button"
                className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
                onClick={() => set("buttons", [...draft.buttons, blankButton()])}
              >
                Add button
              </button>
            ) : null
          }
        >
          {draft.buttons.length === 0 ? (
            <p className="text-xs text-text-disabled">
              Optional. Up to {MAX_BUTTONS} quick replies, links, call buttons or copy-code buttons.
            </p>
          ) : (
            <div className="space-y-3">
              {draft.buttons.map((button, index) => (
                <div key={index} className="rounded-md border border-border p-3">
                  <div className="mb-2 flex items-center justify-between">
                    <p className="text-xs font-medium text-text-secondary">Button {index + 1}</p>
                    <button
                      type="button"
                      className="rounded px-2 text-xs text-danger hover:bg-hover"
                      onClick={() =>
                        set(
                          "buttons",
                          draft.buttons.filter((_, position) => position !== index),
                        )
                      }
                    >
                      Remove
                    </button>
                  </div>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                    <div>
                      <label htmlFor={`button-${index}-type`} className={LABEL_CLASS}>
                        Type
                      </label>
                      <select
                        id={`button-${index}-type`}
                        value={button.type}
                        onChange={(event) =>
                          setButton(index, { type: event.target.value as ButtonType })
                        }
                        className={FIELD_CLASS}
                      >
                        {BUTTON_TYPES.map((type) => (
                          <option key={type} value={type}>
                            {BUTTON_TYPE_LABELS[type]}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label htmlFor={`button-${index}-text`} className={LABEL_CLASS}>
                        Label
                      </label>
                      <input
                        id={`button-${index}-text`}
                        value={button.text}
                        onChange={(event) => setButton(index, { text: event.target.value })}
                        className={FIELD_CLASS}
                      />
                    </div>
                    <div>
                      {button.type === "url" ? (
                        <>
                          <label htmlFor={`button-${index}-url`} className={LABEL_CLASS}>
                            URL
                          </label>
                          <input
                            id={`button-${index}-url`}
                            value={button.url}
                            onChange={(event) => setButton(index, { url: event.target.value })}
                            placeholder="https://example.com"
                            className={FIELD_CLASS}
                          />
                        </>
                      ) : button.type === "phone_number" ? (
                        <>
                          <label htmlFor={`button-${index}-phone`} className={LABEL_CLASS}>
                            Phone number
                          </label>
                          <input
                            id={`button-${index}-phone`}
                            value={button.phone_number}
                            onChange={(event) =>
                              setButton(index, { phone_number: event.target.value })
                            }
                            placeholder="+911234567890"
                            className={FIELD_CLASS}
                          />
                        </>
                      ) : null}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
          {visible.buttons ? <p className="mt-2 text-xs text-danger">{visible.buttons}</p> : null}
        </Section>
      </div>

      {/* --- Live preview ------------------------------------------------------------------- */}
      <div className="space-y-4 lg:sticky lg:top-4 lg:self-start">
        <Section title="Preview">
          <TemplateBubble
            header={draft.header_format === "text" ? draft.header_text : ""}
            body={draft.body_text}
            footer={draft.footer_text}
            mediaFormat={mediaFormat}
            buttons={draft.buttons}
          />
        </Section>

        <Section title="Variables">
          <VariableInspector analysis={analysis} mediaHeader={mediaFormat !== null} />
        </Section>

        {submitError ? <ErrorState message={apiErrorMessage(submitError)} /> : null}

        <div className="flex flex-wrap items-center justify-between gap-2">
          <button
            type="button"
            className={BUTTON_CLASS}
            onClick={() => navigate(editing ? `/templates/${template.id}` : "/templates")}
          >
            Cancel
          </button>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={pending}
              onClick={() => submit(false)}
            >
              Save as draft
            </button>
            <button
              type="button"
              className={PRIMARY_CLASS}
              disabled={pending}
              onClick={() => submit(true)}
            >
              {pending ? "Working…" : "Submit to Meta"}
            </button>
          </div>
        </div>
        <p className="text-xs text-text-disabled">
          A draft stays here and can be edited freely. Submitting sends it to Meta for review —
          once Meta owns it, it can no longer be edited, only cloned.
        </p>
      </div>
    </div>
  );
}
