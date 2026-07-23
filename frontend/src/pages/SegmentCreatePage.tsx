import { useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { SegmentEditor } from "@/features/segments";
import type { Segment } from "@/features/segments";

/**
 * Route page for creating a segment — and for duplicating one.
 *
 * A duplicate arrives as router state carrying the source segment, so the editor opens prefilled
 * with its conditions under a new name. Nothing is copied server-side: the result is an ordinary new
 * segment created by the same POST as any other, and its name must still be unique.
 */
export function SegmentCreatePage(): JSX.Element {
  const location = useLocation();
  const source = (location.state as { duplicateOf?: Segment } | null)?.duplicateOf;

  // A copy starts un-evaluated and needs a distinct name; everything else carries across.
  const seed: Segment | undefined = source
    ? { ...source, name: `${source.name} (copy)`, cached_count: null, last_evaluated_at: null }
    : undefined;

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Segments", to: "/segments" },
          { label: source ? "Duplicate segment" : "New segment" },
        ]}
      />
      <PageHeader
        title={source ? `Duplicate "${source.name}"` : "New segment"}
        description="Build the conditions a contact must satisfy. Nothing is sent — a segment only selects."
      />
      {/* In duplicate mode the editor is still creating: the seed supplies the starting values but
          carries no identity, so it posts a new segment rather than patching the source. */}
      <SegmentEditor key={source?.id ?? "new"} segment={undefined} initial={seed} />
    </PageContainer>
  );
}
