import { useTheme } from "@/lib/theme";

// Placeholder application shell for Step 1 (foundation).
// The full shell — header, collapsible sidebar, command palette, notification
// center (Doc 05 DS-12) — and the real screens are implemented in later steps.
export function AppShell(): JSX.Element {
  const { resolvedTheme, toggle } = useTheme();

  return (
    <div className="min-h-full bg-canvas text-text-primary">
      <header className="flex items-center justify-between border-b border-border bg-surface px-6 py-4">
        <h1 className="text-lg font-semibold">WhatsApp Business Platform</h1>
        <button
          type="button"
          onClick={toggle}
          aria-label="Toggle color theme"
          className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-hover focus-visible:ring-2 focus-visible:ring-focus"
        >
          {resolvedTheme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </header>
      <main className="mx-auto max-w-3xl px-6 py-16 text-center">
        <p className="text-sm font-medium uppercase tracking-wide text-accent">
          Vi Reactivation Team
        </p>
        <h2 className="mt-2 text-2xl font-bold">Foundation ready</h2>
        <p className="mt-3 text-text-secondary">
          Project scaffolding is in place. Authentication, RBAC, and the full
          dashboard are delivered in the following implementation steps.
        </p>
      </main>
    </div>
  );
}
