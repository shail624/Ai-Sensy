import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useNumbers, useWaba } from "@/features/channels/api";
import {
  DefaultChip,
  MetaValueChip,
  NumberStatusChip,
  QualityChip,
  TokenChip,
  WabaStatusChip,
} from "@/features/channels/ChannelBadges";
import { numbersForWaba, numberSummary } from "@/features/channels/selectors";
import { WabaActions } from "@/features/channels/WabaActions";
import type { Waba } from "@/features/channels/types";
import { tokenState, WABA_STATUS_EXPLANATIONS } from "@/features/channels/types";
// The templates feature owns template reads; importing its hook shares one cache rather than
// growing a second query for the same endpoint.
import { useTemplates } from "@/features/templates/api";
import { formatCount, formatDateTime, UNKNOWN } from "@/lib/format";

/**
 * One WhatsApp Business Account in full (Doc 05 B11.5) — its status and credential health, the
 * metadata Meta holds against it, the numbers it owns, and the templates that live on it.
 */
export function WabaDetail({ wabaId }: { wabaId: string }): JSX.Element {
  const navigate = useNavigate();
  const waba = useWaba(wabaId);

  if (waba.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading account…" />
      </PageContainer>
    );
  }

  if (waba.isError || !waba.data) {
    return (
      <PageContainer>
        <Breadcrumbs
          items={[{ label: "Accounts", to: "/channels/accounts" }, { label: "Account" }]}
        />
        <ErrorState message={apiErrorMessage(waba.error)} onRetry={() => void waba.refetch()} />
      </PageContainer>
    );
  }

  const data = waba.data;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[{ label: "Accounts", to: "/channels/accounts" }, { label: data.business_name }]}
      />
      <PageHeader
        title={data.business_name}
        description={`WABA ${data.waba_id}`}
        actions={
          <WabaActions waba={data} onDisconnected={() => navigate("/channels/accounts")} />
        }
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <WabaStatusChip value={data.status} />
        <TokenChip waba={data} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <StatusSection waba={data} />
        <MetadataSection waba={data} />
      </div>

      <div className="mt-4 space-y-4">
        <LinkedNumbersSection waba={data} />
        <LinkedTemplatesSection waba={data} />
      </div>
    </PageContainer>
  );
}

/** What the account's status means, plus the credential facts the platform is able to know. */
function StatusSection({ waba }: { waba: Waba }): JSX.Element {
  const state = tokenState(waba);

  return (
    <Section title="Account status">
      <p className="mb-3 text-sm text-text-secondary">
        {WABA_STATUS_EXPLANATIONS[waba.status] ?? "This account's status came from the platform."}
      </p>

      {state === "expired" || state === "missing" ? (
        <p role="alert" className="mb-3 rounded-md border border-danger px-3 py-2 text-sm text-danger">
          {state === "missing"
            ? "No system-user token is stored. Nothing can send until one is set."
            : "The stored token's recorded expiry has passed. Rotate it before the next send fails."}
        </p>
      ) : state === "expiring" ? (
        <p className="mb-3 rounded-md border border-warning px-3 py-2 text-sm text-warning">
          The stored token expires soon. Rotate it from Edit before it lapses.
        </p>
      ) : null}

      <dl>
        <DefinitionRow label="Status">
          <WabaStatusChip value={waba.status} />
        </DefinitionRow>
        <DefinitionRow label="Credential">
          <TokenChip waba={waba} />
        </DefinitionRow>
        <DefinitionRow label="Token expires">
          {waba.token_expires_at ? formatDateTime(waba.token_expires_at) : "No expiry recorded"}
        </DefinitionRow>
        <DefinitionRow label="Phone numbers">
          {formatCount(waba.phone_number_count)}
        </DefinitionRow>
      </dl>

      <p className="mt-3 text-xs text-text-disabled">
        Meta&apos;s business-verification state is not stored by the platform, so it is not shown
        here — check it in Meta Business Manager. What is shown is the account&apos;s own status and
        whether its credential is present and in date.
      </p>
    </Section>
  );
}

function MetadataSection({ waba }: { waba: Waba }): JSX.Element {
  return (
    <Section title="Metadata">
      <dl>
        <DefinitionRow label="WABA id">
          <span className="break-all font-mono text-xs">{waba.waba_id}</span>
        </DefinitionRow>
        <DefinitionRow label="Meta business id">
          {waba.meta_business_id ? (
            <span className="break-all font-mono text-xs">{waba.meta_business_id}</span>
          ) : (
            UNKNOWN
          )}
        </DefinitionRow>
        <DefinitionRow label="Currency">{waba.currency ?? UNKNOWN}</DefinitionRow>
        <DefinitionRow label="Timezone">{waba.timezone ?? UNKNOWN}</DefinitionRow>
        <DefinitionRow label="Connected">{formatDateTime(waba.created_at)}</DefinitionRow>
        <DefinitionRow label="Last updated">{formatDateTime(waba.updated_at)}</DefinitionRow>
        <DefinitionRow label="Internal id">
          <span className="break-all font-mono text-xs">{waba.id}</span>
        </DefinitionRow>
      </dl>
      <p className="mt-3 text-xs text-text-disabled">
        Currency and timezone feed cost estimation and campaign scheduling.
      </p>
    </Section>
  );
}

/** The numbers this account owns, with the sending capacity and quality they carry. */
function LinkedNumbersSection({ waba }: { waba: Waba }): JSX.Element {
  const numbers = useNumbers();
  const mine = useMemo(
    () => numbersForWaba(numbers.data ?? [], waba.id),
    [numbers.data, waba.id],
  );
  const summary = useMemo(() => numberSummary(mine), [mine]);

  return (
    <Section
      title="Phone numbers"
      action={
        mine.length > 0 ? (
          <Link
            to={`/channels/numbers?waba=${waba.id}`}
            className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
          >
            Open in numbers
          </Link>
        ) : null
      }
    >
      {numbers.isLoading ? (
        <Spinner label="Loading numbers…" />
      ) : numbers.isError ? (
        <ErrorState
          message={apiErrorMessage(numbers.error)}
          onRetry={() => void numbers.refetch()}
        />
      ) : mine.length === 0 ? (
        <EmptyState
          title="No numbers on this account"
          description="Numbers are pulled from Meta — use Sync numbers to fetch them. They cannot be added by hand."
        />
      ) : (
        <>
          <p className="mb-3 text-sm text-text-secondary">
            {formatCount(summary.connected)} connected · {formatCount(summary.healthy)} healthy ·{" "}
            {formatCount(summary.capacity)} messages/second combined
          </p>

          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Number</th>
                  <th scope="col" className="px-3 py-2">Status</th>
                  <th scope="col" className="hidden px-3 py-2 sm:table-cell">Quality</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Tier</th>
                  <th scope="col" className="hidden px-3 py-2 md:table-cell">Limit</th>
                </tr>
              </thead>
              <tbody>
                {mine.map((number) => (
                  <tr key={number.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2">
                      <Link
                        to={`/channels/numbers/${number.id}`}
                        className="font-medium text-text-primary hover:text-accent"
                      >
                        {number.display_number}
                      </Link>
                      <p className="text-xs text-text-secondary">
                        {number.verified_name ?? "No display name"}
                      </p>
                      {number.is_default ? (
                        <div className="mt-1">
                          <DefaultChip />
                        </div>
                      ) : null}
                    </td>
                    <td className="px-3 py-2">
                      <NumberStatusChip value={number.status} />
                    </td>
                    <td className="hidden px-3 py-2 sm:table-cell">
                      <QualityChip value={number.quality_rating} />
                    </td>
                    <td className="hidden px-3 py-2 lg:table-cell">
                      <MetaValueChip value={number.messaging_tier} />
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary md:table-cell">
                      {formatCount(number.mps_limit)}/s
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Section>
  );
}

/** Templates belong to a WABA, so an account's approved set is part of what it is. */
function LinkedTemplatesSection({ waba }: { waba: Waba }): JSX.Element {
  const templates = useTemplates();
  const mine = useMemo(
    () => (templates.data ?? []).filter((template) => template.waba_id === waba.id),
    [templates.data, waba.id],
  );
  const sendable = mine.filter((template) => template.is_sendable).length;

  return (
    <Section
      title="Templates"
      action={
        <Link
          to="/templates"
          className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
        >
          Open templates
        </Link>
      }
    >
      {templates.isLoading ? (
        <Spinner label="Loading templates…" />
      ) : templates.isError ? (
        <ErrorState
          message={apiErrorMessage(templates.error)}
          onRetry={() => void templates.refetch()}
        />
      ) : mine.length === 0 ? (
        <EmptyState
          title="No templates on this account"
          description="Templates are created and approved per account."
        />
      ) : (
        <>
          <p className="mb-2 text-sm text-text-secondary">
            {formatCount(sendable)} of {formatCount(mine.length)} can be broadcast
          </p>
          <ul className="flex flex-wrap gap-2">
            {mine.slice(0, 12).map((template) => (
              <li key={template.id}>
                <Link
                  to={`/templates/${template.id}`}
                  className="inline-flex items-center gap-2 rounded-full border border-border px-3 py-1 font-mono text-xs text-text-secondary hover:bg-hover"
                >
                  {template.name}
                  <span className={template.is_sendable ? "text-success" : "text-text-disabled"}>
                    {template.is_sendable ? "✓" : "·"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
          {mine.length > 12 ? (
            <p className="mt-2 text-xs text-text-disabled">
              and {formatCount(mine.length - 12)} more.
            </p>
          ) : null}
        </>
      )}
    </Section>
  );
}
