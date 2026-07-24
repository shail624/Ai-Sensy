import { Download, Tag, TagsIcon, Trash2, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui";
import { BulkActionDialog, type BulkMode } from "@/features/contacts/BulkActionDialog";
import type { SegmentRule } from "@/features/contacts/types";
import { useHasPermission } from "@/lib/auth";
import { useIsCompact } from "@/lib/useMediaQuery";

interface Props {
  selectedIds: Set<string>;
  onClear: () => void;
  /** The active filters — an export addresses contacts by rule, not by id. */
  rules: SegmentRule[];
  /**
   * Pixels the page must keep free at its bottom edge. Non-zero only on phones, where the bar is
   * docked and therefore out of flow; the page cannot know the height because the number of actions
   * depends on the caller's permissions and on how they wrap.
   */
  onDockedHeightChange?: (px: number) => void;
}

/**
 * The sticky bulk action bar (Doc 05 DS-14, B3.1). Docked to the bottom edge on phones, inline from
 * `md` up. Actions follow the permissions the API enforces: editing and deleting need
 * `contacts:write`, exporting needs `contacts:export`, and a button the caller cannot use is absent
 * rather than disabled.
 */
export function BulkActionsBar({
  selectedIds,
  onClear,
  rules,
  onDockedHeightChange,
}: Props): JSX.Element | null {
  const canWrite = useHasPermission("contacts:write");
  const canExport = useHasPermission("contacts:export");
  const compact = useIsCompact();
  const [mode, setMode] = useState<BulkMode | null>(null);
  const barRef = useRef<HTMLDivElement>(null);
  const selectionSize = selectedIds.size;

  // The docked bar is out of flow, so the page has to give back exactly as much room as it occupies
  // — which depends on how many actions this caller may see, and on how they wrap.
  useEffect(() => {
    const report = onDockedHeightChange;
    if (!report) return;
    const element = barRef.current;
    if (!element || !compact || selectionSize === 0) {
      report(0);
      return;
    }
    const measure = (): void => report(element.offsetHeight + 32);
    measure();
    if (typeof ResizeObserver === "undefined") return;
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [compact, selectionSize, canWrite, canExport, onDockedHeightChange]);

  if (selectionSize === 0) return null;
  const ids = [...selectedIds];

  return (
    <>
      <div
        ref={barRef}
        className="fixed inset-x-4 bottom-4 z-30 flex flex-wrap items-center gap-2 rounded-xl border border-accent bg-accent-soft px-3 py-2.5 shadow-lg md:static md:mb-3 md:flex-nowrap md:gap-3 md:px-4 md:shadow-none"
      >
        <span className="text-sm font-semibold text-accent">
          {selectedIds.size.toLocaleString()} selected
        </span>
        <span className="hidden flex-1 md:block" />

        {canWrite ? (
          <>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<Tag className="h-4 w-4" />}
              onClick={() => setMode("add_tags")}
            >
              Tag
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setMode("remove_tags")}>
              Untag
            </Button>
            <Button
              variant="secondary"
              size="sm"
              leftIcon={<TagsIcon className="h-4 w-4" />}
              onClick={() => setMode("set_attributes")}
            >
              Attribute
            </Button>
          </>
        ) : null}

        {canExport ? (
          <Button
            variant="secondary"
            size="sm"
            leftIcon={<Download className="h-4 w-4" />}
            onClick={() => setMode("export")}
          >
            Export
          </Button>
        ) : null}

        {canWrite ? (
          <Button
            variant="danger"
            size="sm"
            leftIcon={<Trash2 className="h-4 w-4" />}
            onClick={() => setMode("delete")}
          >
            Delete
          </Button>
        ) : null}

        <Button variant="ghost" size="sm" leftIcon={<X className="h-4 w-4" />} onClick={onClear}>
          Clear
        </Button>
      </div>


      {mode ? (
        <BulkActionDialog
          mode={mode}
          ids={ids}
          rules={rules}
          onClose={() => setMode(null)}
          onCompleted={onClear}
        />
      ) : null}
    </>
  );
}
