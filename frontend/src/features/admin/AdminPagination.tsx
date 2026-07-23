import { formatCount } from "@/lib/format";

const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1 text-sm hover:bg-hover disabled:opacity-50";

interface Props {
  page: number;
  totalPages: number;
  total: number;
  /** Singular noun for the row type — "user", "role", "key", "entry". */
  noun: string;
  /** Plural, where adding an "s" would be wrong ("entry" → "entries"). */
  nounPlural?: string;
  filtered: boolean;
  onGoTo: (page: number) => void;
  /** True when the server returned fewer rows than it holds, so the caption can say so. */
  truncatedTo?: { loaded: number; available: number };
}

/**
 * The shared pagination footer for every administration list.
 *
 * One implementation rather than four near-identical copies, and one place that states the same
 * uncomfortable truth: these lists page over what the endpoint returned, which may be less than
 * the whole set. Saying it here means no list can quietly forget to.
 */
export function AdminPagination({
  page,
  totalPages,
  total,
  noun,
  nounPlural,
  filtered,
  onGoTo,
  truncatedTo,
}: Props): JSX.Element {
  const plural = nounPlural ?? `${noun}s`;

  return (
    <>
      <nav
        aria-label="Pagination"
        className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-text-secondary"
      >
        <p>
          {filtered ? "Matching: " : ""}
          {formatCount(total)} {total === 1 ? noun : plural}
          {totalPages > 1 ? ` · page ${page} of ${totalPages}` : ""}
        </p>
        {totalPages > 1 ? (
          <div className="flex items-center gap-2">
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={page <= 1}
              onClick={() => onGoTo(page - 1)}
            >
              Previous
            </button>
            <button
              type="button"
              className={BUTTON_CLASS}
              disabled={page >= totalPages}
              onClick={() => onGoTo(page + 1)}
            >
              Next
            </button>
          </div>
        ) : null}
      </nav>

      {truncatedTo && truncatedTo.available > truncatedTo.loaded ? (
        <p className="mt-2 text-xs text-text-disabled">
          {formatCount(truncatedTo.available)} {plural} exist; the{" "}
          {formatCount(truncatedTo.loaded)} most recent are loaded here.
        </p>
      ) : null}
    </>
  );
}
