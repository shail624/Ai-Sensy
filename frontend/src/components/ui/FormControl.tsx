import {
  forwardRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

export type ControlSize = "sm" | "md" | "lg";

const CONTROL_BASE =
  "w-full min-w-0 rounded-control border border-border bg-surface text-text-primary transition-[border-color,box-shadow,background-color] placeholder:text-text-disabled hover:border-border-strong focus-visible:border-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus disabled:cursor-not-allowed disabled:bg-surface-2 disabled:text-text-disabled disabled:opacity-70";

const CONTROL_SIZES: Record<ControlSize, string> = {
  sm: "h-8 px-2.5 text-xs max-md:h-10",
  md: "h-9 px-3 text-sm max-md:h-10",
  lg: "h-11 px-3.5 text-sm",
};

function controlClasses(
  size: ControlSize,
  invalid: boolean,
  className: string,
): string {
  return `${CONTROL_BASE} ${CONTROL_SIZES[size]} ${
    invalid ? "border-danger focus-visible:border-danger focus-visible:ring-danger" : ""
  } ${className}`;
}

export interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "size"> {
  controlSize?: ControlSize;
  invalid?: boolean;
  leadingIcon?: ReactNode;
  trailingAction?: ReactNode;
  containerClassName?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  {
    controlSize = "md",
    invalid = false,
    leadingIcon,
    trailingAction,
    containerClassName = "w-full",
    className = "",
    ...props
  },
  ref,
): JSX.Element {
  const input = (
    <input
      {...props}
      ref={ref}
      data-slot="input"
      aria-invalid={invalid || props["aria-invalid"] || undefined}
      className={controlClasses(
        controlSize,
        invalid,
        `${leadingIcon ? "pl-9" : ""} ${trailingAction ? "pr-10" : ""} ${className}`,
      )}
    />
  );

  if (!leadingIcon && !trailingAction) return input;

  return (
    <div className={`relative min-w-0 ${containerClassName}`}>
      {leadingIcon ? (
        <span className="pointer-events-none absolute left-3 top-1/2 z-10 flex -translate-y-1/2 items-center text-text-disabled">
          {leadingIcon}
        </span>
      ) : null}
      {input}
      {trailingAction ? (
        <span className="absolute right-1.5 top-1/2 z-10 flex -translate-y-1/2 items-center">
          {trailingAction}
        </span>
      ) : null}
    </div>
  );
});

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  controlSize?: ControlSize;
  invalid?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { controlSize = "md", invalid = false, className = "", ...props },
  ref,
): JSX.Element {
  return (
    <select
      {...props}
      ref={ref}
      data-slot="select"
      aria-invalid={invalid || props["aria-invalid"] || undefined}
      className={controlClasses(controlSize, invalid, `pr-8 ${className}`)}
    />
  );
});

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  invalid?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(function Textarea(
  { invalid = false, className = "", rows = 4, ...props },
  ref,
): JSX.Element {
  return (
    <textarea
      {...props}
      ref={ref}
      rows={rows}
      data-slot="textarea"
      aria-invalid={invalid || props["aria-invalid"] || undefined}
      className={`${CONTROL_BASE} min-h-24 resize-y px-3 py-2.5 text-sm ${
        invalid ? "border-danger focus-visible:border-danger focus-visible:ring-danger" : ""
      } ${className}`}
    />
  );
});

interface FieldProps {
  htmlFor: string;
  label: ReactNode;
  children: ReactNode;
  description?: ReactNode;
  error?: ReactNode;
  optional?: boolean;
  className?: string;
}

export function Field({
  htmlFor,
  label,
  children,
  description,
  error,
  optional = false,
  className = "",
}: FieldProps): JSX.Element {
  return (
    <div className={`min-w-0 ${className}`}>
      <label
        htmlFor={htmlFor}
        className="mb-1.5 flex items-center gap-2 text-xs font-semibold text-text-secondary"
      >
        <span>{label}</span>
        {optional ? <span className="font-normal text-text-disabled">Optional</span> : null}
      </label>
      {children}
      {error ? (
        <p role="alert" className="mt-1.5 text-xs text-danger">
          {error}
        </p>
      ) : description ? (
        <p className="mt-1.5 text-xs leading-relaxed text-text-secondary">{description}</p>
      ) : null}
    </div>
  );
}
