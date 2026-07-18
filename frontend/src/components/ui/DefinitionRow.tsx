import type { ReactNode } from "react";

interface DefinitionRowProps {
  label: string;
  children: ReactNode;
}

/** One label/value row inside a `<dl>`. */
export function DefinitionRow({ label, children }: DefinitionRowProps): JSX.Element {
  return (
    <div className="grid grid-cols-3 gap-2 py-1.5">
      <dt className="text-xs font-medium text-text-secondary">{label}</dt>
      <dd className="col-span-2 text-sm text-text-primary">{children}</dd>
    </div>
  );
}
