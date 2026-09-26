import { Info } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

interface InfoTooltipProps {
  /** Accessible name of the trigger, e.g. "About quality rating". */
  label: string;
  /** One or more lines; each renders as a bullet like the reference hint cards. */
  lines: ReactNode[];
  className?: string;
}

/**
 * An (i) hint that opens above its icon on hover or keyboard focus: white card, 10px text,
 * 6px radius, fading and scaling in over ~200ms.
 */
export function InfoTooltip({ label, lines, className = "" }: InfoTooltipProps): JSX.Element {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <span className={`relative inline-flex ${className}`}>
      <button
        type="button"
        aria-label={label}
        aria-describedby={open ? id : undefined}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
        }}
        className="inline-flex rounded-full text-black/25 transition-colors hover:text-black/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:text-white/30"
      >
        <Info aria-hidden className="h-[19px] w-[19px]" strokeWidth={2.25} />
      </button>
      <span
        id={id}
        role="tooltip"
        className={`pointer-events-none absolute bottom-full left-1/2 z-40 mb-1.5 w-max max-w-[240px] -translate-x-1/2 origin-bottom rounded-md bg-surface px-2 py-1 text-[10px] font-medium leading-[20px] text-[#222] shadow-[0_2px_10px_rgba(0,0,0,0.15)] transition-[opacity,transform,visibility] duration-200 ease-[cubic-bezier(0.4,0,0.2,1)] dark:text-text-primary ${
          open ? "scale-100 opacity-100" : "invisible scale-75 opacity-0"
        }`}
      >
        {lines.map((line, index) => (
          <span key={index} className="block">• {line}</span>
        ))}
      </span>
    </span>
  );
}
