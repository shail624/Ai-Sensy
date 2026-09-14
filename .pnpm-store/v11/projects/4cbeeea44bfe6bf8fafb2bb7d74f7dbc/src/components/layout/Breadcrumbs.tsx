import { ChevronRight, Home } from "lucide-react";
import { Fragment } from "react";
import { Link } from "react-router-dom";

export interface Crumb {
  label: string;
  to?: string;
}

/** Reusable breadcrumb trail. The last crumb is the current page (`aria-current`). */
export function Breadcrumbs({ items }: { items: Crumb[] }): JSX.Element {
  return (
    <nav aria-label="Breadcrumb" className="mb-4 text-xs text-text-secondary">
      <ol className="flex min-h-6 flex-wrap items-center gap-1.5">
        {items.map((crumb, index) => {
          const isLast = index === items.length - 1;
          return (
            <Fragment key={`${crumb.label}-${index}`}>
              <li>
                {crumb.to && !isLast ? (
                  <Link
                    to={crumb.to}
                    className="inline-flex items-center gap-1 rounded-md hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                  >
                    {index === 0 && crumb.label === "Dashboard" ? <Home aria-hidden className="h-3.5 w-3.5" /> : null}
                    {crumb.label}
                  </Link>
                ) : (
                  <span
                    aria-current={isLast ? "page" : undefined}
                    className={isLast ? "text-text-primary" : undefined}
                  >
                    {crumb.label}
                  </span>
                )}
              </li>
              {!isLast ? (
                <li aria-hidden className="text-text-disabled">
                  <ChevronRight className="h-3.5 w-3.5" />
                </li>
              ) : null}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}
