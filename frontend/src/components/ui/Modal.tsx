import { useEffect, useRef, type ReactNode } from "react";

interface ModalProps {
  title: string;
  onClose: () => void;
  children: ReactNode;
  /**
   * `sheet` docks the surface to the bottom edge on phones and returns to the centred dialog from
   * `sm` up — the bottom-sheet pattern Doc 05 B3.1 specifies for mobile filters. Default unchanged.
   */
  variant?: "center" | "sheet" | "drawer";
}

const SHELL: Record<"center" | "sheet" | "drawer", string> = {
  center: "flex items-start justify-center overflow-y-auto p-4 sm:p-8",
  sheet: "flex items-end justify-center sm:items-start sm:overflow-y-auto sm:p-8",
  drawer: "flex items-end justify-center sm:items-stretch sm:justify-end",
};

const PANEL: Record<"center" | "sheet" | "drawer", string> = {
  center: "w-full max-w-lg rounded-lg",
  sheet: "max-h-[85vh] w-full overflow-y-auto rounded-t-2xl sm:max-w-lg sm:rounded-lg",
  drawer:
    "max-h-[92vh] w-full overflow-y-auto rounded-t-2xl sm:h-full sm:max-h-none sm:max-w-2xl sm:rounded-none sm:rounded-l-2xl",
};

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Accessible modal dialog — focus moves in on open, Tab is trapped inside, Escape and backdrop click
 * close it, focus returns to whatever opened it, and the surface is labelled by its heading
 * (Doc 05 DS-10 "Focus management").
 */
export function Modal({ title, onClose, children, variant = "center" }: ModalProps): JSX.Element {
  const panelRef = useRef<HTMLDivElement>(null);
  // Kept in a ref so an inline `onClose` arrow does not re-run the focus effect on every render.
  const closeRef = useRef(onClose);
  closeRef.current = onClose;

  useEffect(() => {
    const invoker = document.activeElement as HTMLElement | null;
    panelRef.current?.focus();

    function onKeyDown(event: KeyboardEvent): void {
      if (event.key === "Escape") {
        closeRef.current();
        return;
      }
      if (event.key !== "Tab") return;
      const panel = panelRef.current;
      if (!panel) return;
      // No visibility filter: the dialogs put real controls behind `sr-only` (the file input), and
      // those belong in the tab order exactly as they are.
      const focusable = [...panel.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (focusable.length === 0) {
        event.preventDefault();
        panel.focus();
        return;
      }
      const first = focusable[0]!;
      const last = focusable[focusable.length - 1]!;
      const active = document.activeElement;
      if (event.shiftKey && (active === first || active === panel)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      // Returning focus to the invoker keeps a keyboard user where they were (DS-10).
      invoker?.focus?.();
    };
  }, []);

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
