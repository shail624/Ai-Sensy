import type { ReactNode } from "react";

export type BadgeTone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-surface-2 text-text-secondary",
  accent: "bg-accent-soft text-accent-on-soft",
  success: "bg-success-soft text-success-on-soft",
  warning: "bg-warning-soft text-warning-on-soft",
  danger: "bg-danger-soft text-danger-on-soft",
  info: "bg-info-soft text-info-on-soft",
};

const DOT: Record<BadgeTone, string> = {
  neutral: "bg-text-disabled",
  accent: "bg-accent",
  success: "bg-success",
  warning: "bg-warning",
  danger: "bg-danger",
  info: "bg-info",
};

interface BadgeProps {
  children: ReactNode;
  tone?: BadgeTone;
  /** Show a leading status dot. */
  dot?: boolean;
  /** Hover explanation, where the label alone cannot carry the nuance. */
  title?: string;
  className?: string;
}

/** A compact status/label pill (Doc 05 DS). Use `dot` for live-status semantics. */
export function Badge({
  children,
  tone = "neutral",
  dot = false,
  title,
  className = "",
}: BadgeProps): JSX.Element {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}
    >
      {dot ? <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${DOT[tone]}`} /> : null}
      {children}
    </span>
  );
}
