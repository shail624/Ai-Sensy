import { Link } from "react-router-dom";

import { PageContainer, PageHeader, visibleNavItems } from "@/components/layout";
import { MyWorkQueue } from "@/features/tasks";
import { useAuth } from "@/lib/auth";

export function DashboardPage(): JSX.Element {
  const { hasPermission } = useAuth();
  // Module entry cards: every destination the user may reach, except Dashboard itself and Settings.
  const moduleCards = visibleNavItems(hasPermission).filter(
    (item) => item.path !== "/" && item.path !== "/settings",
  );

  return (
    <PageContainer>
      <PageHeader title="Dashboard" description="Your WhatsApp Business Platform workspace." />

      {/* My Work Queue (Doc 14 §11) — mounted additively above the module cards. */}
      <section aria-label="My Work Queue" className="mb-6">
        <h2 className="mb-3 text-sm font-semibold text-text-primary">My Work Queue</h2>
        <MyWorkQueue />
      </section>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {moduleCards.map((item) => {
          const card = (
            <div
              className={`flex h-full flex-col rounded-lg border border-border bg-surface p-4 ${
                item.available ? "hover:border-accent" : "opacity-70"
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <h2 className="text-sm font-semibold text-text-primary">{item.label}</h2>
                {!item.available ? (
                  <span className="shrink-0 rounded bg-surface-2 px-2 py-0.5 text-xs text-text-disabled">
                    Coming Soon
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-text-secondary">
                {item.available
                  ? `Open ${item.label}.`
                  : `${item.label} is not available yet.`}
              </p>
            </div>
          );

          return item.available ? (
            <Link
              key={item.path}
              to={item.path}
              className="rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
            >
              {card}
            </Link>
          ) : (
            <div key={item.path} aria-disabled>
              {card}
            </div>
          );
        })}
      </div>
    </PageContainer>
  );
}
