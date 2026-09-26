import type { ReactNode } from "react";

/** Standard page surface: the reference's light grey canvas, full width, with compact gutters. */
export function PageContainer({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div data-slot="page-container" className="relative min-h-full w-full bg-[#f9f9f9] dark:bg-canvas">
      <div className="mx-auto w-full max-w-[1480px] px-4 pb-6 sm:px-6 lg:px-[30px]">{children}</div>
    </div>
  );
}
