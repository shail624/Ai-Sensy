import { Lightbulb } from "lucide-react";

/** The reference row action: a 30px round icon button in the brand teal. */
export const ROW_ICON =
  "flex h-[30px] w-[30px] items-center justify-center rounded-full text-[var(--color-nav-bg)] transition-colors duration-150 hover:bg-[#ebf5f3] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-accent";

/** The reference "Quick Guide" strip at the top of each Manage page: what the page is for. */
export function QuickGuide({ eyebrow, text }: { eyebrow: string; text: string }): JSX.Element {
  return (
    <div className="flex items-start gap-3 rounded-[8px] bg-gradient-to-r from-[#eefaf3] to-surface p-4 dark:from-accent-soft">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-[var(--color-nav-bg)] shadow-sm dark:bg-surface-2 dark:text-accent">
        <Lightbulb aria-hidden className="h-[18px] w-[18px]" />
      </span>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wide text-[#2f8a4f]">{eyebrow}</p>
        <p className="text-base font-semibold text-black dark:text-text-primary">Quick Guide</p>
        <p className="mt-0.5 text-sm text-[#6e6e6e] dark:text-text-secondary">{text}</p>
      </div>
    </div>
  );
}
