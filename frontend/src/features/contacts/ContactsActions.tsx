import { ChevronDown, Download, History } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui";
import { BulkActionDialog } from "@/features/contacts/BulkActionDialog";
import type { SegmentRule } from "@/features/contacts/types";
import { useHasPermission } from "@/lib/auth";

interface Props {
  rules: SegmentRule[];
}

/** Page-level contact actions that apply to the current server-filtered view. */
export function ContactsActions({ rules }: Props): JSX.Element | null {
  const canExport = useHasPermission("contacts:export");
  const [open, setOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function closeOnOutside(event: MouseEvent): void {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function closeOnEscape(event: KeyboardEvent): void {
      if (event.key !== "Escape") return;
      setOpen(false);
      containerRef.current?.querySelector<HTMLButtonElement>('button[aria-haspopup="menu"]')?.focus();
    }
    document.addEventListener("mousedown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("mousedown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [open]);

  if (!canExport) return null;

  return (
    <>
      <div ref={containerRef} className="relative">
        <Button
          variant="secondary"
          aria-haspopup="menu"
          aria-expanded={open}
          rightIcon={<ChevronDown aria-hidden className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />}
          onClick={() => setOpen((value) => !value)}
        >
          Actions
        </Button>
        {open ? (
          <div role="menu" aria-label="Contact actions" className="absolute right-0 z-30 mt-2 w-56 rounded-xl border border-border bg-surface p-1.5 shadow-lg">
            <button
              type="button"
              role="menuitem"
              onClick={() => { setOpen(false); setExporting(true); }}
              className="flex min-h-10 w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm font-medium text-text-primary hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <Download aria-hidden className="h-4 w-4 text-text-secondary" />
              Export current view
            </button>
            <Link
              to="/downloads"
              role="menuitem"
              onClick={() => setOpen(false)}
              className="flex min-h-10 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-text-primary hover:bg-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              <History aria-hidden className="h-4 w-4 text-text-secondary" />
              Export history
            </Link>
          </div>
        ) : null}
      </div>
      {exporting ? (
        <BulkActionDialog
          mode="export"
          ids={[]}
          rules={rules}
          onClose={() => setExporting(false)}
          onCompleted={() => setExporting(false)}
        />
      ) : null}
    </>
  );
}
