import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";

export interface Crumb {
  label: string;
  to?: string;
}

/**
 * The reference has no breadcrumb trail: a top-level page shows nothing, and a page inside
 * another (a campaign, a customer, a template) shows one "← Back to …" link to its parent.
 */
export function Breadcrumbs({ items }: { items: Crumb[] }): JSX.Element | null {
  const parent = [...items.slice(0, -1)].reverse().find((crumb) => crumb.to && crumb.label !== "Dashboard");
  if (!parent?.to) return null;
  return (
    <nav aria-label="Breadcrumb" className="pt-3 text-sm">
      <Link
        to={parent.to}
        className="inline-flex items-center gap-1.5 rounded-md font-medium text-[var(--color-nav-bg)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-accent"
      >
        <ArrowLeft aria-hidden className="h-4 w-4" /> Back to {parent.label}
      </Link>
    </nav>
  );
}
