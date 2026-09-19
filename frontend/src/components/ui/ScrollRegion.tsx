import type { ReactNode } from "react";

interface Props {
  /** Names the region for somebody who reaches it by keyboard or hears it announced. */
  label: string;
  children: ReactNode;
  className?: string;
}

/**
 * A horizontally scrolling area that a keyboard can reach (WCAG 2.1.1).
 *
 * A wide table inside a plain `overflow-x-auto` div is scrollable by mouse or trackpad and by
 * nothing else: without a focusable element inside it, there is no way to put the caret in it and
 * scroll with the arrow keys, so the columns past the fold are simply unreachable. That is a real
 * failure and an invisible one — it only appears where the content is actually wider than the box,
 * which on a table of plain text usually means a phone, not the desktop it was designed on.
 *
 * Making the container itself focusable is the standard remedy. The label matters as much as the
 * tab stop: an unnamed focus stop on a bare div tells a screen-reader user nothing about what they
 * have landed on.
 */
export function ScrollRegion({ label, children, className }: Props): JSX.Element {
  return (
    <div
      role="region"
      aria-label={label}
      tabIndex={0}
      className={`overflow-x-auto focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${className ?? ""}`}
    >
      {children}
    </div>
  );
}
