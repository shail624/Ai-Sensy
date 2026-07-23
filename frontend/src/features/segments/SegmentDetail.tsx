import { useMemo } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useAttributeDefinitions,
  useSegment,
  useSegmentPreview,
} from "@/features/segments/api";
import { RuleSummary } from "@/features/segments/RuleSummary";
import { SegmentActions } from "@/features/segments/SegmentActions";
import {
  CountChip,
  DynamicChip,
  MatchTypeChip,
  RuleCountChip,
} from "@/features/segments/SegmentBadges";
import type { Segment } from "@/features/segments/types";
import { isStale } from "@/features/segments/types";
import { formatAge, formatCount, formatDateTime, UNKNOWN } from "@/lib/format";

/**
 * One segment in full — what it selects, how many it currently matches, and who those contacts are.
 */
export function SegmentDetail({ segmentId }: { segmentId: string }): JSX.Element {
  const navigate = useNavigate();
  const segment = useSegment(segmentId);

  if (segment.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading segment…" />
      </PageContainer>
    );
  }

  if (segment.isError || !segment.data) {
    return (
      <PageContainer>
        <Breadcrumbs items={[{ label: "Segments", to: "/segments" }, { label: "Segment" }]} />
        <ErrorState message={apiErrorMessage(segment.error)} onRetry={() => void segment.refetch()} />
      </PageContainer>
    );
  }

  const data = segment.data;

  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Segments", to: "/segments" }, { label: data.name }]} />
      <PageHeader
        title={data.name}
        description={data.description ?? "No description"}
        actions={<SegmentActions segment={data} onDeleted={() => navigate("/segments")} />}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <CountChip segment={data} />
        <MatchTypeChip value={data.match_type} />
        <RuleCountChip count={data.rules.length} />
        <DynamicChip dynamic={data.is_dynamic} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <ConditionsSection segment={data} />
        <RecordSection segment={data} />
      </div>

      <div className="mt-4">
        <MatchingContactsSection segment={data} />
      </div>
    </PageContainer>
  );
}

function ConditionsSection({ segment }: { segment: Segment }): JSX.Element {
  const attributes = useAttributeDefinitions();

  return (
    <Section title="Conditions">
      {attributes.isLoading ? (
        <Spinner label="Loading fields…" />
      ) : (
        <RuleSummary
          rules={segment.rules}
          matchType={segment.match_type}
          attributes={attributes.data ?? []}
        />
      )}
    </Section>
  );
}

function RecordSection({ segment }: { segment: Segment }): JSX.Element {
  return (
    <Section title="Record">
      {isStale(segment) ? (
        <p className="mb-3 rounded-md border border-warning px-3 py-2 text-sm text-warning">
          This segment has not been evaluated since its conditions last changed, so it has no saved
          size. Refresh it to compute one — the live list below is accurate either way.
        </p>
      ) : null}

      <dl>
        <DefinitionRow label="Saved size">
          <CountChip segment={segment} />
        </DefinitionRow>
        <DefinitionRow label="Last evaluated">
          {segment.last_evaluated_at ? (
            <>
              {formatDateTime(segment.last_evaluated_at)}{" "}
              <span className="text-text-disabled">({formatAge(segment.last_evaluated_at)})</span>
            </>
          ) : (
            "Never"
          )}
        </DefinitionRow>
        <DefinitionRow label="Logic">
          <MatchTypeChip value={segment.match_type} />
        </DefinitionRow>
        <DefinitionRow label="Evaluation">
          <DynamicChip dynamic={segment.is_dynamic} />
        </DefinitionRow>
        <DefinitionRow label="Description">{segment.description ?? UNKNOWN}</DefinitionRow>
        <DefinitionRow label="Created">{formatDateTime(segment.created_at)}</DefinitionRow>
        <DefinitionRow label="Last updated">{formatDateTime(segment.updated_at)}</DefinitionRow>
        <DefinitionRow label="Segment id">
          <span className="break-all font-mono text-xs">{segment.id}</span>
        </DefinitionRow>
      </dl>

      <p className="mt-3 text-xs text-text-disabled">
        The saved size is a cached figure, recomputed on demand. Campaigns resolve the segment live
        at dispatch, so a campaign always sends to whoever matches at that moment — not to this
        number.
      </p>
    </Section>
  );
}

/**
 * Who the segment matches right now.
 *
 * Evaluated live against the compiled rule tree, so this is the authoritative membership — not the
 * cached count. Cursor-paginated at 50 by contract, and `cursor` is not a declared parameter, so
 * this shows the first page and reports the true total beside it.
 */
function MatchingContactsSection({ segment }: { segment: Segment }): JSX.Element {
  const preview = useSegmentPreview(segment.id);

  const rows = useMemo(() => preview.data?.data ?? [], [preview.data]);
  const total = preview.data?.page.total ?? rows.length;
  const truncated = total > rows.length;

  return (
    <Section
      title="Matching contacts"
      action={
        <Link
          to="/contacts"
          className="rounded-md border border-border px-2 py-1 text-xs hover:bg-hover"
        >
          Open contacts
        </Link>
      }
    >
      {preview.isLoading ? (
        <Spinner label="Evaluating segment…" />
      ) : preview.isError ? (
        <ErrorState
          message={apiErrorMessage(preview.error)}
          onRetry={() => void preview.refetch()}
        />
      ) : rows.length === 0 ? (
        <EmptyState
          title="No contacts match"
          description={
            segment.rules.length === 0
              ? "This segment has no conditions, so it should match everyone — the contact list itself may be empty."
              : "No contact currently satisfies these conditions."
          }
        />
      ) : (
        <>
          <p className="mb-3 text-sm text-text-secondary">
            {formatCount(total)} contact{total === 1 ? "" : "s"} match right now
          </p>

          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Contact</th>
                  <th scope="col" className="hidden px-3 py-2 sm:table-cell">Phone</th>
                  <th scope="col" className="hidden px-3 py-2 lg:table-cell">Opt-in</th>
                  <th scope="col" className="hidden px-3 py-2 xl:table-cell">Last contacted</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((contact) => (
                  <tr key={contact.id} className="border-b border-border last:border-0">
                    <td className="px-3 py-2">
                      <Link
                        to={`/contacts/${contact.id}`}
                        className="font-medium text-text-primary hover:text-accent"
                      >
                        {contact.full_name ?? "Unnamed"}
                      </Link>
                      <p className="text-xs text-text-secondary sm:hidden">{contact.phone_e164}</p>
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary sm:table-cell">
                      {contact.phone_e164}
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                      {contact.opt_in_status}
                    </td>
                    <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
                      {contact.last_contacted_at ? formatAge(contact.last_contacted_at) : "never"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {truncated ? (
            <p className="mt-2 text-xs text-text-disabled">
              {formatCount(total)} contacts match; the first {formatCount(rows.length)} are shown
              here. Paging beyond the first page is not available from this screen.
            </p>
          ) : null}
        </>
      )}
    </Section>
  );
}
