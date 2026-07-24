import { useEffect, useRef, type ReactNode } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /**
   * `sheet` docks the surface to the bottom edge on phones and returns to the centred dialog from
   * `sm` up — the bottom-sheet pattern Doc 05 B3.1 specifies for mobile filters. Default unchanged.
   */
  variant?: "center" | "sheet";
}

const SHELL: Record<"center" | "sheet", string> = {
  center: "flex items-start justify-center overflow-y-auto p-4 sm:p-8",
  sheet: "flex items-end justify-center sm:items-start sm:overflow-y-auto sm:p-8",
};

const PANEL: Record<"center" | "sheet", string> = {
  center: "w-full max-w-lg rounded-lg",
  sheet: "max-h-[85vh] w-full overflow-y-auto rounded-t-2xl sm:max-w-lg sm:rounded-lg",
};

/**
 * Accessible modal dialog — focus is moved in on open, Escape and backdrop click close it, and the
 * surface is labelled by its heading (Doc 05 accessibility baseline).
 */
export function Modal({ title, onClose, children, variant = "center" }: ModalProps): JSX.Element {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    panelRef.current?.focus();
    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className={`fixed inset-0 z-50 bg-black/50 ${SHELL[variant]}`}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
        className={`border border-border bg-surface shadow-lg focus:outline-none ${PANEL[variant]}`}
      >
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <h2 className="text-sm font-semibold text-text-primary">{title}</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close dialog"
            className="rounded px-2 text-text-secondary hover:bg-hover"
          >
            ×
          </button>
        </header>
        <div className="px-4 py-3">{children}</div>
      </div>
    </div>
  );
}
