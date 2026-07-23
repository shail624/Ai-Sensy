import { ArrowUpRight } from "lucide-react";
import { Link } from "react-router-dom";

import { PageContainer, visibleNavItems } from "@/components/layout";
import { MyWorkQueue } from "@/features/tasks";
import { useAuth } from "@/lib/auth";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

export function DashboardPage(): JSX.Element {
  const { hasPermission, user } = useAuth();
  const firstName = user?.full_name.trim().split(/\s+/)[0] ?? "there";
  // Module entry cards: every destination the user may reach, except Dashboard itself and Settings.
  const moduleCards = visibleNavItems(hasPermission).filter(
    (item) => item.path !== "/" && item.path !== "/settings",
  );

  return (
    <PageContainer>
      {/* Hero — a warmer landing than a bare page title. */}
      <div className="mb-8 overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        <div className="relative px-6 py-7 sm:px-8">
          <div
            aria-hidden
            className="brand-gradient pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full opacity-10 blur-2xl"
          />
          <p className="text-sm font-medium text-accent">{greeting()},</p>
          <h1 className="mt-1 text-2xl font-bold tracking-tight text-text-primary">{firstName} 👋</h1>
          <p className="mt-2 max-w-xl text-sm text-text-secondary">
            {"Here's your WhatsApp Business workspace. Jump into a conversation, launch a campaign, or clear today's follow-ups below."}
          </p>
        </div>
      </div>

      <section aria-label="My Work Queue" className="mb-8">
        <h2 className="mb-3 text-sm font-semibold text-text-primary">My Work Queue</h2>
        <MyWorkQueue />
      </section>

      <section aria-label="Modules">
        <h2 className="mb-3 text-sm font-semibold text-text-primary">Explore</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {moduleCards.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                to={item.path}
                // The label alone is the link's purpose; the description is supporting text. Naming
                // the link explicitly keeps a card whose description happens to mention another
                // module (e.g. Campaigns → "templates") from matching that module by name.
                aria-label={item.label}
                className="group flex items-start gap-4 rounded-xl border border-border bg-surface p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
              >
                <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-accent-soft text-accent transition-colors group-hover:bg-accent group-hover:text-accent-fg">
                  <Icon aria-hidden className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5">
                    <span className="font-semibold text-text-primary">{item.label}</span>
                    <ArrowUpRight
                      aria-hidden
                      className="h-4 w-4 text-text-disabled opacity-0 transition-opacity group-hover:opacity-100"
                    />
                  </span>
                  <span className="mt-1 block text-sm leading-relaxed text-text-secondary">
                    {item.description}
                  </span>
                </span>
              </Link>
            );
          })}
        </div>
      </section>
    </PageContainer>
  );
}
