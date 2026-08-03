import type { ReactNode } from "react";

/** Standard page width and compact responsive gutters inside the persistent application shell. */
export function PageContainer({ children }: { children: ReactNode }): JSX.Element {
  return (
    <div
      data-slot="page-container"
      className="relative mx-auto w-full max-w-[1480px] px-4 py-4 sm:px-5 sm:py-5 lg:px-7 lg:py-6"
    >
      {children}
    </div>
  );
}
