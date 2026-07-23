import type { ReactNode } from "react";

/** Standard page width + padding wrapper for content rendered inside the app shell. */
export function PageContainer({ children }: { children: ReactNode }): JSX.Element {
  return <div className="mx-auto max-w-6xl p-4 sm:p-6">{children}</div>;
}
