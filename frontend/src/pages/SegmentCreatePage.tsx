import { useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { SegmentEditor } from "@/features/segments";
import type { Segment, SegmentSeed } from "@/features/segments";
import {
  audiencePresetById,
  createAudiencePresetSeed,
  isAudiencePresetId,
} from "@/features/segments/audiencePresets";

/**
 * Route page for creating a segment — and for duplicating one.
 *
 * A duplicate arrives as router state carrying the source segment, so the editor opens prefilled
 * with its conditions under a new name. Nothing is copied server-side: the result is an ordinary new
 * segment created by the same POST as any other, and its name must still be unique.
 */
export function SegmentCreatePage(): JSX.Element {
  const location = useLocation();
  const state = location.state as
    | { duplicateOf?: Segment; audiencePresetId?: unknown }
    | null;
  const source = state?.duplicateOf;
  const presetId = isAudiencePresetId(state?.audiencePresetId)
    ? state.audiencePresetId
    : null;
  const preset = presetId ? audiencePresetById(presetId) : null;

  // A copy starts un-evaluated and needs a distinct name; everything else carries across.
  const seed: SegmentSeed | undefined = source
    ? {
        name: `${source.name} (copy)`,
        description: source.description,
        match_type: source.match_type,
        rules: source.rules,
      }
    : presetId
      ? createAudiencePresetSeed(presetId)
      : undefined;
  const modeLabel = source ? "Duplicate segment" : preset ? preset.label : "New segment";

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Segments", to: "/segments" },
          { label: modeLabel },
        ]}
      />
      <PageHeader
        eyebrow={preset ? "Audience preset" : undefined}
        title={source ? `Duplicate "${source.name}"` : preset ? preset.label : "New segment"}
        description={
          preset
            ? "Review the prepared condition and date before saving. This creates a normal reusable segment."
            : "Build the conditions a contact must satisfy. Nothing is sent — a segment only selects."
        }
      />
      {/* In duplicate mode the editor is still creating: the seed supplies the starting values but
          carries no identity, so it posts a new segment rather than patching the source. */}
      <SegmentEditor key={source?.id ?? presetId ?? "new"} segment={undefined} initial={seed} />
    </PageContainer>
  );
}
