import type { ReactNode } from "react";

import { ApiStatus } from "./ApiStatus";

interface ManagePageHeaderProps {
  title: string;
  /** Right-aligned primary action(s), e.g. "Create Template". */
  actions?: ReactNode;
}

/**
 * The reference's Manage-page bar: 60px, white, soft glow, a 20px regular title on the left and
 * the page's primary action on the right. It replaces the app header on those pages.
 */
export function ManagePageHeader({ title, actions }: ManagePageHeaderProps): JSX.Element {
  return (
    <header data-slot="page-header" className="sticky top-0 z-20 flex h-[60px] shrink-0 items-center justify-between gap-3 bg-surface pl-6 pr-[30px] shadow-card">
      <h1 className="mr-auto truncate text-xl font-normal leading-[23px] text-black dark:text-text-primary">{title}</h1>
      <ApiStatus className="hidden md:flex" />
      {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
    </header>
  );
}

/** The reference's primary action button in a Manage header (37px, 6px radius, teal). */
export const MANAGE_PRIMARY_ACTION =
  "inline-flex h-[37px] items-center justify-center rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white transition-colors duration-200 hover:bg-[#08393d] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus";
