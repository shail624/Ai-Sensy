import { EmptyState } from "@/components/ui";
import type { VariableAnalysis } from "@/features/templates/components";

interface Props {
  analysis: VariableAnalysis;
  /** Shown when the header carries media: it has no text, so it can declare no variables. */
  mediaHeader?: boolean;
}

/**
 * Every variable the definition declares, where it lives and whether the numbering is legal.
 *
 * Meta numbers variables from `{{1}}` per component with no gaps and rejects anything else, so a
 * gap is reported as a problem rather than quietly counted — catching it here is the difference
 * between a corrected draft and a rejection that costs a review cycle.
 *
 * What a variable *resolves to* is deliberately not set here. A template declares positions; the
 * values are bound per recipient when a campaign maps them to a contact field, attribute or literal.
 * Showing an editable "sample value" on this screen would imply the template stores one.
 */
export function VariableInspector({ analysis, mediaHeader = false }: Props): JSX.Element {
  const uses = [...analysis.header, ...analysis.body];

  return (
    <div>
      {analysis.problems.length > 0 ? (
        <ul role="alert" className="mb-3 space-y-1">
          {analysis.problems.map((problem) => (
            <li
              key={problem}
              className="rounded-md border border-danger px-3 py-2 text-sm text-danger"
            >
              {problem}
            </li>
          ))}
        </ul>
      ) : null}

      {uses.length === 0 ? (
        <EmptyState
          title="No variables"
          description={
            mediaHeader
              ? "Every recipient receives the same text. The media header's file is supplied per send."
              : "Every recipient receives the same text."
          }
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Variable</th>
                  <th scope="col" className="px-3 py-2">Component</th>
                  <th scope="col" className="px-3 py-2 text-right">Occurrences</th>
                </tr>
              </thead>
              <tbody>
                {uses.map((use) => (
                  <tr
                    key={`${use.component}-${use.index}`}
                    className="border-b border-border last:border-0"
                  >
                    <td className="px-3 py-2 font-mono text-text-primary">{`{{${use.index}}}`}</td>
                    <td className="px-3 py-2 capitalize text-text-secondary">{use.component}</td>
                    <td className="px-3 py-2 text-right text-text-secondary">{use.occurrences}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-2 text-xs text-text-disabled">
            A send must supply {analysis.total} value{analysis.total === 1 ? "" : "s"}. Values are
            bound per recipient when a campaign maps each variable to a contact field, a custom
            attribute or fixed text — the template itself only declares the positions.
          </p>
        </>
      )}
    </div>
  );
}
