import { Check, ChevronDown, Copy, Pencil } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

import { Skeleton } from "@/components/ui";
import type { AccountSummary } from "@/features/channels/accountSummary";
import { useBusinessProfile } from "@/features/channels/api";
import { VERTICAL_LABELS, type BusinessVertical } from "@/features/channels/types";
import { apiErrorMessage } from "@/lib/api/errors";
import { useCopiedFlag } from "@/lib/useCopiedFlag";

import { DASH_CARD } from "./dashboardStyles";
import { EditBusinessProfileDialog } from "./EditBusinessProfileDialog";

function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? parts[parts.length - 1]?.[0] ?? "" : "")).toUpperCase() || "W";
}

function ProfileField({ label, children }: { label: string; children: ReactNode }): JSX.Element {
  return (
    <div>
      <p className="text-xs leading-[17px] text-[#6e6e6e] dark:text-text-secondary">{label}</p>
      <div className="mt-1 whitespace-pre-line break-words text-sm leading-[21px] text-[#4a4a4a] dark:text-text-primary">{children}</div>
    </div>
  );
}

interface WabaProfileCardProps {
  summary: AccountSummary | null;
  loading: boolean;
  canManage: boolean;
}

/** Right-column business card: name, category, number, chat link, editable profile. */
export function WabaProfileCard({ summary, loading, canManage }: WabaProfileCardProps): JSX.Element | null {
  const [copied, markCopied] = useCopiedFlag();
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const bodyId = useId();
  const numberId = summary?.number?.id ?? "";
  const profile = useBusinessProfile(numberId, Boolean(numberId));

  if (loading) {
    return (
      <section aria-label="WhatsApp business profile" className={`${DASH_CARD} px-5 py-2.5`}>
        <Skeleton className="h-28 w-full" />
      </section>
    );
  }
  if (!summary?.waba) return null;

  const { waba, number } = summary;
  const digits = number?.display_number.replace(/\D/g, "") ?? "";
  const chatLink = digits ? `wa.me/${digits}` : null;
  const data = profile.data;
  const websites = data?.websites ?? [];
  const vertical = data?.vertical ? VERTICAL_LABELS[data.vertical as BusinessVertical] ?? data.vertical : null;

  return (
    <section aria-label="WhatsApp business profile" className={`${DASH_CARD} px-5 py-2.5`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-normal leading-[21px] text-text-primary">{number?.verified_name ?? waba.business_name}</h2>
          <p className="text-xs uppercase leading-[17px] text-[#6e6e6e] dark:text-text-secondary">{vertical ?? "WhatsApp Business"}</p>
        </div>
        {canManage && number && data ? (
          <button
            type="button"
            aria-label="Edit business profile"
            title="Edit business profile"
            onClick={() => setEditing(true)}
            className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full bg-[#ebf5f3] text-[var(--color-nav-bg)] transition-colors duration-150 hover:bg-[#d6ebe7] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:bg-accent-soft dark:text-accent"
          >
            <Pencil aria-hidden className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>

      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xl font-semibold leading-[23px] text-[var(--color-nav-bg)] dark:text-accent">
            {number ? `+ ${digits}` : "No number yet"}
          </p>
          {chatLink ? (
            <button
              type="button"
              title="Copy"
              onClick={() => {
                void navigator.clipboard?.writeText(`https://${chatLink}`).then(markCopied, () => undefined);
              }}
              className="mt-2 flex items-center gap-1 text-xs text-[#717171] transition-colors hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-text-secondary"
            >
              {chatLink}
              {copied ? <Check aria-hidden className="h-3.5 w-3.5 text-success" /> : <Copy aria-hidden className="h-3.5 w-3.5" />}
              <span className="sr-only">{copied ? "Link copied" : "Copy chat link"}</span>
            </button>
          ) : null}
        </div>
        {data?.profile_picture_url ? (
          <img src={data.profile_picture_url} alt="" className="h-[70px] w-[70px] shrink-0 rounded-full object-cover" />
        ) : (
          <span aria-hidden className="flex h-[70px] w-[70px] shrink-0 items-center justify-center rounded-full bg-[#ebf5f3] text-2xl font-semibold text-[var(--color-nav-bg)] dark:bg-accent-soft dark:text-accent">
            {initials(waba.business_name)}
          </span>
        )}
      </div>

      {number ? (
        <>
          <button
            type="button"
            aria-expanded={open}
            aria-controls={bodyId}
            onClick={() => setOpen((value) => !value)}
            className="mt-1 inline-flex items-center gap-3 rounded-md py-2 text-sm text-[var(--color-nav-bg)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-accent"
          >
            {open ? "Hide Profile" : "View Profile"}
            <span aria-hidden className="flex h-[15px] w-[15px] items-center justify-center rounded-full border border-current">
              <ChevronDown className={`h-3 w-3 transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
            </span>
          </button>
          <div id={bodyId} className={`grid transition-[grid-template-rows] duration-150 ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
            <div className={`min-h-0 overflow-hidden ${open ? "visible" : "invisible"}`}>
              <div className="space-y-4 pb-3 pt-2">
                {profile.isLoading ? <Skeleton className="h-24 w-full" /> : null}
                {profile.isError ? (
                  <p role="alert" className="text-sm text-danger">Could not load the profile from Meta: {apiErrorMessage(profile.error)}</p>
                ) : null}
                {data ? (
                  <>
                    <ProfileField label="Description">{data.description || data.about || "—"}</ProfileField>
                    <ProfileField label="Address">{data.address || "—"}</ProfileField>
                    <ProfileField label="Email">
                      {data.email ? <a href={`mailto:${data.email}`} className="text-xs text-[var(--color-nav-bg)] hover:underline dark:text-accent">{data.email}</a> : "—"}
                    </ProfileField>
                    <ProfileField label="Website">
                      {websites.length > 0
                        ? websites.map((site) => (
                          <a key={site} href={site} target="_blank" rel="noreferrer" className="block text-xs text-[var(--color-nav-bg)] hover:underline dark:text-accent">{site}</a>
                        ))
                        : "—"}
                    </ProfileField>
                  </>
                ) : null}
              </div>
            </div>
          </div>
        </>
      ) : null}

      {editing && data && number ? (
        <EditBusinessProfileDialog numberId={number.id} profile={data} onClose={() => setEditing(false)} />
      ) : null}
    </section>
  );
}
