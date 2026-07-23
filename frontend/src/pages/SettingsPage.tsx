import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { SETTINGS_SECTIONS } from "@/features/settings";
import { useAuth } from "@/lib/auth";

/**
 * `/settings` has no content of its own — it lands on the first section this user can read.
 *
 * Sending everyone to Organization would give someone with only `auth:self` a refusal as their
 * first impression of their own preferences page.
 */
export function SettingsIndexRedirect(): JSX.Element {
  const { hasPermission } = useAuth();
  const first = SETTINGS_SECTIONS.find((section) => hasPermission(section.permission));
  return first ? <Navigate to={first.path} replace /> : <Outlet />;
}

/**
 * The settings shell (Doc 05 B11.11) — sub-navigation plus the active section.
 *
 * Only the sections the signed-in user can actually read are offered, and the routes carry the same
 * permission, so typing a URL gets the same honest answer the navigation gives.
 */
export function SettingsPage(): JSX.Element {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const sections = SETTINGS_SECTIONS.filter((section) => hasPermission(section.permission));

  const active = sections.find((section) => location.pathname.startsWith(section.path));

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          { label: "Settings", to: sections[0]?.path },
          ...(active ? [{ label: active.label }] : []),
        ]}
      />
      <PageHeader
        title="Settings"
        description={active?.description ?? "Organization, configuration and your own preferences."}
      />

      {sections.length === 0 ? (
        <EmptyState
          title="You don't have access to this area"
          description="Ask an administrator if you need access."
        />
      ) : (
        <>
          <nav aria-label="Settings sections" className="mb-4 flex flex-wrap gap-2">
            {sections.map((section) => (
              <NavLink
                key={section.key}
                to={section.path}
                className={({ isActive }) =>
                  `rounded-md border px-3 py-1 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
                    isActive
                      ? "border-accent text-accent"
                      : "border-border text-text-secondary hover:bg-hover"
                  }`
                }
              >
                {section.label}
              </NavLink>
            ))}
          </nav>

          <Outlet />
        </>
      )}
    </PageContainer>
  );
}
