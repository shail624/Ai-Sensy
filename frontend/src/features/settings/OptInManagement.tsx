import { Pencil, Plus, X } from "lucide-react";
import { useEffect, useState } from "react";

import { ErrorState, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useHasPermission,
  useInboxOperations,
  useUpdateInboxOperations,
} from "@/features/settings/api";
import {
  ConfigureDialog,
  MANAGE_CARD,
  MANAGE_OUTLINE,
  MANAGE_PRIMARY,
  ResponsePreview,
  Toggle,
} from "@/features/settings/managePrimitives";
import type { InboxOperationsPolicy, InboxOperationsUpdate } from "@/features/settings/types";

type Kind = "opt-out" | "opt-in";

interface ConsentDraft {
  enabled: boolean;
  "opt-in": { keywords: string[]; responseEnabled: boolean; response: string };
  "opt-out": { keywords: string[]; responseEnabled: boolean; response: string };
}

const COPY: Record<Kind, { title: string; description: string; response: string; responseHelp: string }> = {
  "opt-out": {
    title: "Opt-out Keywords",
    description: "The user will have to type exactly one of these messages on which they should be automatically opted-out.",
    response: "Opt-out Response",
    responseHelp: "Setup a response message for opt-out user keywords",
  },
  "opt-in": {
    title: "Opt-in Keywords",
    description: "The user will have to type exactly one of these messages on which they should be automatically opted-in.",
    response: "Opt-in Response",
    responseHelp: "Setup a response message for opt-in user keywords",
  },
};


function fromPolicy(policy: InboxOperationsPolicy): ConsentDraft {
  const consent = policy.consent;
  return {
    enabled: consent?.enabled ?? false,
    "opt-in": {
      keywords: consent?.opt_in_keywords?.length ? [...consent.opt_in_keywords] : ["START", "YES"],
      responseEnabled: consent?.opt_in_response_enabled ?? false,
      response: consent?.opt_in_response_body ?? "",
    },
    "opt-out": {
      keywords: consent?.opt_out_keywords?.length ? [...consent.opt_out_keywords] : ["STOP", "UNSUBSCRIBE"],
      responseEnabled: consent?.opt_out_response_enabled ?? false,
      response: consent?.opt_out_response_body ?? "",
    },
  };
}

/** Everything else in the policy is sent back untouched; only `consent` changes here. */
function toUpdate(policy: InboxOperationsPolicy, draft: ConsentDraft): InboxOperationsUpdate {
  const clean = (list: string[]): string[] => list.map((keyword) => keyword.trim()).filter(Boolean);
  return {
    assignment_mode: policy.assignment_mode,
    auto_mark_read: policy.auto_mark_read,
    send_read_receipts: policy.send_read_receipts,
    show_typing_indicators: policy.show_typing_indicators ?? false,
    working_hours: policy.working_hours,
    automatic_replies: policy.automatic_replies,
    auto_resolve: policy.auto_resolve,
    consent: {
      enabled: draft.enabled,
      opt_in_keywords: clean(draft["opt-in"].keywords),
      opt_out_keywords: clean(draft["opt-out"].keywords),
      opt_in_response_enabled: draft["opt-in"].responseEnabled,
      opt_in_response_body: draft["opt-in"].response.trim(),
      opt_out_response_enabled: draft["opt-out"].responseEnabled,
      opt_out_response_body: draft["opt-out"].response.trim(),
    },
  };
}

/** Same rules the combined inbox-policy form enforces, so neither screen can save what the other rejects. */
export function validateConsent(draft: ConsentDraft): string | null {
  const optIn = draft["opt-in"].keywords.map((k) => k.trim()).filter(Boolean);
  const optOut = draft["opt-out"].keywords.map((k) => k.trim()).filter(Boolean);
  if (draft.enabled && (!optIn.length || !optOut.length)) {
    return "Enabled consent handling needs at least one opt-in and one opt-out keyword.";
  }
  const normalizedIn = new Set(optIn.map((keyword) => keyword.toUpperCase()));
  const overlap = optOut.find((keyword) => normalizedIn.has(keyword.toUpperCase()));
  if (overlap) return `“${overlap}” cannot be both an opt-in and opt-out keyword.`;
  if (draft["opt-in"].responseEnabled && !draft["opt-in"].response.trim()) return "An enabled opt-in response needs message text.";
  if (draft["opt-out"].responseEnabled && !draft["opt-out"].response.trim()) return "An enabled opt-out response needs message text.";
  return null;
}




/**
 * The reference Opt-in Management page: a consent switch, then one card per direction with the
 * exact keywords on the left and the configured customer response on the right.
 */
export function OptInManagement(): JSX.Element {
  const canManage = useHasPermission("settings:manage");
  const policy = useInboxOperations();
  const update = useUpdateInboxOperations();
  const [draft, setDraft] = useState<ConsentDraft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [configuring, setConfiguring] = useState<Kind | null>(null);

  useEffect(() => {
    if (policy.data) setDraft(fromPolicy(policy.data));
  }, [policy.data]);

  if (policy.isLoading || (!draft && !policy.isError)) return <Spinner label="Loading opt-in settings…" />;
  if (policy.isError || !policy.data || !draft) {
    return <ErrorState message={apiErrorMessage(policy.error)} onRetry={() => void policy.refetch()} />;
  }
  const saved = policy.data;
  const current = draft;

  function save(next: ConsentDraft = current): void {
    const problem = validateConsent(next);
    setError(problem);
    if (problem) return;
    update.mutate(toUpdate(saved, next));
  }

  function setKind(kind: Kind, patch: Partial<ConsentDraft[Kind]>): void {
    setDraft({ ...current, [kind]: { ...current[kind], ...patch } });
  }

  const locked = !canManage;

  return (
    <div className="space-y-8">
      <section className={`${MANAGE_CARD} px-8 py-8`} aria-labelledby="consent-switch-title">
        <div className="flex items-start justify-between gap-6">
          <div>
            <h2 id="consent-switch-title" className="text-base font-normal text-black dark:text-text-primary">Recognize consent keywords</h2>
            <p className="mt-4 text-sm text-[#6e6e6e] dark:text-text-secondary">
              Exact whole-message matches update the contact&apos;s opt-in state. A sentence that merely contains a keyword is ignored.
            </p>
          </div>
          <Toggle
            checked={current.enabled}
            disabled={locked || update.isPending}
            label="Recognize consent keywords"
            onChange={(enabled) => {
              const next = { ...current, enabled };
              setDraft(next);
              save(next);
            }}
          />
        </div>
      </section>

      {(["opt-out", "opt-in"] as const).map((kind) => {
        const copy = COPY[kind];
        const side = current[kind];
        return (
          <section key={kind} aria-labelledby={`${kind}-title`} className={`${MANAGE_CARD} grid gap-8 px-[42px] pb-[35px] pt-[42px] lg:grid-cols-2`}>
            <div>
              <h2 id={`${kind}-title`} className="text-base font-normal text-[#4a4a4a] dark:text-text-primary">{copy.title}</h2>
              <p className="mt-3 text-sm leading-[21px] text-[#6e6e6e] dark:text-text-secondary">{copy.description}</p>
              <ul className="mt-8 space-y-4">
                {side.keywords.map((keyword, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <input
                      aria-label={`${copy.title} ${index + 1}`}
                      value={keyword}
                      disabled={locked}
                      placeholder="Enter Keywords"
                      onChange={(event) => setKind(kind, { keywords: side.keywords.map((k, i) => (i === index ? event.target.value : k)) })}
                      className="h-[42px] w-[200px] rounded-[8px] bg-[#f0f0f0] px-[15px] text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:opacity-60 dark:bg-surface-2 dark:text-text-primary"
                    />
                    {!locked && side.keywords.length > 1 ? (
                      <button
                        type="button"
                        aria-label={`Remove ${keyword || "keyword"}`}
                        onClick={() => setKind(kind, { keywords: side.keywords.filter((_, i) => i !== index) })}
                        className="flex h-8 w-8 items-center justify-center rounded-full text-black/40 transition-colors hover:bg-hover hover:text-danger"
                      >
                        <X aria-hidden className="h-4 w-4" />
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>
              {!locked ? (
                <>
                  <button type="button" onClick={() => setKind(kind, { keywords: [...side.keywords, ""] })} className="mt-8 inline-flex h-[37px] items-center gap-1.5 rounded-md px-2 text-sm font-medium text-[var(--color-nav-bg)] transition-colors hover:bg-[#ebf5f3] dark:text-accent">
                    <Plus aria-hidden className="h-4 w-4" /> Add more
                  </button>
                  <div className="mt-8">
                    <button type="button" onClick={() => save()} disabled={update.isPending} className={MANAGE_PRIMARY}>
                      {update.isPending ? "Saving…" : "Save Settings"}
                    </button>
                  </div>
                </>
              ) : null}
            </div>
            <div>
              <div className="flex items-start justify-between gap-3">
                <h3 className="pt-1 text-base font-normal text-[#4a4a4a] dark:text-text-primary">{copy.response}</h3>
                {!locked ? (
                  <button type="button" onClick={() => setConfiguring(kind)} className={MANAGE_OUTLINE}><Pencil aria-hidden className="h-[18px] w-[18px]" />Configure</button>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-[#6e6e6e] dark:text-text-secondary">{copy.responseHelp}</p>
              <div className="mt-8">
                <ResponsePreview body={side.responseEnabled ? side.response : ""} />
              </div>
            </div>
          </section>
        );
      })}

      {error ? <p role="alert" className="text-sm text-danger">{error}</p> : null}
      {update.error ? <ErrorState message={apiErrorMessage(update.error)} /> : null}
      {update.isSuccess && !error ? <p role="status" className="text-sm text-success-on-soft">Settings saved.</p> : null}
      {locked ? <p className="text-sm text-text-secondary">Read-only — changing opt-in settings needs settings:manage.</p> : null}

      {configuring ? (
        <ConfigureDialog
          description={`Send a regular text message to the customer after their ${configuring} is recorded.`}
          switchLabel={`Send ${configuring} response`}
          enabled={current[configuring].responseEnabled}
          body={current[configuring].response}
          onClose={() => setConfiguring(null)}
          onSave={(responseEnabled, response) => {
            const next = { ...current, [configuring]: { ...current[configuring], responseEnabled, response } };
            setDraft(next);
            save(next);
          }}
        />
      ) : null}
    </div>
  );
}
