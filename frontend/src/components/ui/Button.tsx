import type { ButtonHTMLAttributes, ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "subtle";
export type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  block?: boolean;
}

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:opacity-55";

const VARIANTS: Record<ButtonVariant, string> = {
  primary: "bg-accent text-accent-fg hover:bg-accent-strong shadow-sm",
  secondary: "border border-border bg-surface text-text-primary hover:bg-hover",
  ghost: "text-text-secondary hover:bg-hover hover:text-text-primary",
  subtle: "bg-accent-soft text-accent hover:bg-accent hover:text-accent-fg",
  danger: "bg-danger text-white hover:opacity-90 shadow-sm",
};

// Desktop density is unchanged; below `md` every button clears DS-10's 40x40 touch target.
const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 max-md:h-10 px-3 text-xs",
  md: "h-9 max-md:h-10 px-4 text-sm",
  lg: "h-11 px-5 text-sm",
};

/** The one button in the system — every call-to-action routes through here (Doc 05 DS). */
export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  leftIcon,
  rightIcon,
  block = false,
  className = "",
  children,
  disabled,
  ...props
}: ButtonProps): JSX.Element {
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`${BASE} ${VARIANTS[variant]} ${SIZES[size]} ${block ? "w-full" : ""} ${className}`}
    >
      {loading ? (
        <span
          aria-hidden
          className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-current border-t-transparent opacity-70"
        />
      ) : (
        leftIcon
      )}
      {children}
      {!loading ? rightIcon : null}
    </button>
  );
}
