function chip(tone: string): string {
  return `inline-flex items-center rounded-full border px-2 py-0.5 text-xs ${tone}`;
}

/**
 * The default pipeline.
 *
 * Exactly one exists at a time and it cannot be archived, so the badge marks a constraint rather
 * than a preference.
 */
export function DefaultChip(): JSX.Element {
  return (
    <span
      title="New leads fall into this pipeline. It cannot be archived."
      className={chip("border-accent text-accent")}
    >
      Default
    </span>
  );
}

/** A stage that ends the journey — nothing follows it. */
export function TerminalChip(): JSX.Element {
  return (
    <span title="An end state — a lead that reaches it has finished." className={chip("border-success text-success")}>
      Final
    </span>
  );
}

export function StageCountChip({ count }: { count: number }): JSX.Element {
  if (count === 0) {
    return (
      <span
        title="A pipeline with no stages cannot hold a lead anywhere."
        className={chip("border-warning text-warning")}
      >
        No stages
      </span>
    );
  }
  return (
    <span className={chip("border-border text-text-secondary")}>
      {count} stage{count === 1 ? "" : "s"}
    </span>
  );
}

/** The stage's place in the order, as the server stores it (0-based, shown 1-based). */
export function PositionChip({ position }: { position: number }): JSX.Element {
  return (
    <span className={chip("border-border font-mono text-text-disabled")}>{position + 1}</span>
  );
}
