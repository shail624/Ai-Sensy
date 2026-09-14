import { BookmarkPlus, CalendarRange, Film, Megaphone, ShieldCheck, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";

import { Button, ErrorState, Field, Input, Modal, Select } from "@/components/ui";
import type { Campaign } from "@/features/campaigns/types";
import {
  apiErrorMessage,
  fromSharedFilters,
  toSharedFilters,
  useCreateHistoryView,
  useDeleteHistoryView,
  type HistoryView,
} from "@/features/chat-history/api";
import type { InboxFilters } from "@/features/inbox/types";

interface Props {
  filters: InboxFilters;
  campaigns: Campaign[];
  savedViews: HistoryView[];
  canReadCampaigns: boolean;
  canAudit: boolean;
  canManageViews: boolean;
  onApply: (filters: InboxFilters) => void;
  onClose: () => void;
}

export function HistoryFiltersDialog({
  filters,
  campaigns,
  savedViews,
  canReadCampaigns,
  canAudit,
  canManageViews,
  onApply,
  onClose,
}: Props): JSX.Element {
  const [draft, setDraft] = useState(filters);
  const [viewName, setViewName] = useState("");
  const createView = useCreateHistoryView();
  const deleteView = useDeleteHistoryView();
  const invalidRange = Boolean(
    draft.dateFrom && draft.dateTo && draft.dateFrom > draft.dateTo,
  );

  useEffect(() => setDraft(filters), [filters]);

  return (
    <Modal title="Chat History filters" variant="sheet" onClose={onClose}>
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-xl border border-border bg-surface-2 p-3">
          <CalendarRange aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-accent" />
          <p className="text-xs leading-relaxed text-text-secondary">
            Dates filter by the conversation&apos;s latest activity. Campaign and media filters inspect
            the persisted message ledger, not only the currently loaded page.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Field htmlFor="history-date-from" label="From" optional>
            <Input
              id="history-date-from"
              type="date"
              value={draft.dateFrom ?? ""}
              max={draft.dateTo}
              onChange={(event) =>
                setDraft({ ...draft, dateFrom: event.target.value || undefined })
              }
            />
          </Field>
          <Field
            htmlFor="history-date-to"
            label="Through"
            optional
            error={invalidRange ? "Through must be on or after From." : undefined}
          >
            <Input
              id="history-date-to"
              type="date"
              value={draft.dateTo ?? ""}
              min={draft.dateFrom}
              invalid={invalidRange}
              onChange={(event) =>
                setDraft({ ...draft, dateTo: event.target.value || undefined })
              }
            />
          </Field>
        </div>

        {canReadCampaigns ? (
          <Field htmlFor="history-campaign" label="Campaign" optional>
            <Select
              id="history-campaign"
              value={draft.campaign ?? ""}
              onChange={(event) =>
                setDraft({ ...draft, campaign: event.target.value || undefined })
              }
            >
              <option value="">All campaigns</option>
              {campaigns.map((campaign) => (
                <option key={campaign.id} value={campaign.id}>
                  {campaign.name}
                </option>
              ))}
            </Select>
          </Field>
        ) : null}

        <div className="grid gap-2 sm:grid-cols-2">
          <label className="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border border-border p-3 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus">
            <input
              type="checkbox"
              checked={Boolean(draft.hasMedia)}
              onChange={(event) => setDraft({ ...draft, hasMedia: event.target.checked || undefined })}
              className="h-4 w-4 accent-[var(--color-accent)]"
            />
            <Film aria-hidden className="h-4 w-4 text-accent" />
            <span className="text-xs font-semibold text-text-primary">Contains media</span>
          </label>
          {canAudit ? (
            <label className="flex min-h-12 cursor-pointer items-center gap-3 rounded-xl border border-border p-3 has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-focus">
              <input
                type="checkbox"
                checked={Boolean(draft.hasAudit)}
                onChange={(event) => setDraft({ ...draft, hasAudit: event.target.checked || undefined })}
                className="h-4 w-4 accent-[var(--color-accent)]"
              />
              <ShieldCheck aria-hidden className="h-4 w-4 text-accent" />
              <span className="text-xs font-semibold text-text-primary">Has audit activity</span>
            </label>
          ) : null}
        </div>

        {savedViews.length > 0 ? (
          <section aria-label="Team shared Chat History views" className="space-y-2">
            <p className="text-xs font-bold text-text-primary">Team-shared views</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {savedViews.map((view) => (
                <div key={view.id} className="flex items-center rounded-xl border border-border bg-surface-2">
                  <button
                    type="button"
                    onClick={() => setDraft(fromSharedFilters(view.filters))}
                    className="min-w-0 flex-1 truncate px-3 py-2.5 text-left text-xs font-semibold text-text-primary"
                  >
                    {view.name}
                  </button>
                  {canManageViews ? (
                    <button
                      type="button"
                      aria-label={`Delete ${view.name} view`}
                      disabled={deleteView.isPending}
                      onClick={() => deleteView.mutate(view.id)}
                      className="mr-1 rounded-lg p-2 text-text-disabled hover:bg-hover hover:text-danger"
                    >
                      <Trash2 aria-hidden className="h-3.5 w-3.5" />
                    </button>
                  ) : null}
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {canManageViews ? (
          <form
            className="space-y-2 rounded-xl border border-border p-3"
            onSubmit={(event) => {
              event.preventDefault();
              const name = viewName.trim();
              if (!name || invalidRange) return;
              createView.mutate(
                { name, filters: toSharedFilters(draft) },
                { onSuccess: () => setViewName("") },
              );
            }}
          >
            <div className="flex items-center gap-2">
              <BookmarkPlus aria-hidden className="h-4 w-4 text-accent" />
              <p className="text-xs font-bold text-text-primary">Save for the team</p>
            </div>
            <div className="flex gap-2">
              <Input
                aria-label="Shared view name"
                value={viewName}
                maxLength={80}
                placeholder="Example: August media follow-up"
                onChange={(event) => setViewName(event.target.value)}
              />
              <Button
                type="submit"
                variant="secondary"
                loading={createView.isPending}
                disabled={!viewName.trim() || invalidRange}
              >
                Save
              </Button>
            </div>
          </form>
        ) : null}

        {createView.error || deleteView.error ? (
          <ErrorState message={apiErrorMessage(createView.error ?? deleteView.error)} />
        ) : null}

        <div className="flex items-center justify-between gap-3 border-t border-border pt-3">
          <Button
            type="button"
            variant="ghost"
            onClick={() => setDraft({})}
          >
            Clear all
          </Button>
          <Button
            type="button"
            disabled={invalidRange}
            leftIcon={<Megaphone aria-hidden className="h-4 w-4" />}
            onClick={() => {
              onApply(draft);
              onClose();
            }}
          >
            Apply filters
          </Button>
        </div>
      </div>
    </Modal>
  );
}
