import type { ReactNode } from "react";

/** Standard page width + padding wrapper for content rendered inside the app shell. */
export function PageContainer({ children }: { children: ReactNode }): JSX.Element {
  return <div className="relative mx-auto w-full max-w-[1440px] p-4 sm:p-6 lg:p-8">{children}</div>;
}
