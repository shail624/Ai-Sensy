import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "./Button";

interface PaginationProps {
  hasPrevious: boolean;
  hasNext: boolean;
  onPrevious: () => void;
  onNext: () => void;
  label?: string;
  summary?: ReactNode;
  busy?: boolean;
  compact?: boolean;
  className?: string;
}

/** Cursor-safe previous/next navigation shared by list and workspace surfaces. */
export function Pagination({
  hasPrevious,
  hasNext,
  onPrevious,
  onNext,
  label = "Pagination",
  summary,
  busy = false,
  compact = false,
  className = "",
}: PaginationProps): JSX.Element {
  return (
    <nav
      aria-label={label}
      className={`flex min-h-12 items-center gap-3 ${
        summary ? "justify-between" : "justify-end"
      } ${compact ? "border-t border-border bg-surface px-3 py-2" : "border-t border-border pt-4"} ${className}`}
    >
      {summary ? <div className="min-w-0 text-xs text-text-secondary">{summary}</div> : null}
      <div className="flex shrink-0 items-center gap-2">
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={!hasPrevious || busy}
          onClick={onPrevious}
          leftIcon={<ChevronLeft aria-hidden className="h-3.5 w-3.5" />}
        >
          Previous
        </Button>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          disabled={!hasNext || busy}
          onClick={onNext}
          rightIcon={<ChevronRight aria-hidden className="h-3.5 w-3.5" />}
        >
          Next
        </Button>
      </div>
    </nav>
  );
}
