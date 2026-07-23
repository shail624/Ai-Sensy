import type { ReactNode } from "react";

export type BadgeTone = "neutral" | "accent" | "success" | "warning" | "danger" | "info";

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-surface-2 text-text-secondary",
  accent: "bg-accent-soft text-accent",
  success: "bg-success-soft text-success",
  warning: "bg-warning-soft text-warning",
  danger: "bg-danger-soft text-danger",
  info: "bg-info-soft text-info",
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
  className?: string;
}

/** A compact status/label pill (Doc 05 DS). Use `dot` for live-status semantics. */
export function Badge({ children, tone = "neutral", dot = false, className = "" }: BadgeProps): JSX.Element {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}
    >
      {dot ? <span aria-hidden className={`h-1.5 w-1.5 rounded-full ${DOT[tone]}`} /> : null}
      {children}
    </span>
  );
}
