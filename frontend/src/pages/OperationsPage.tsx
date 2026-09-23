import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { OPERATIONS_SECTIONS } from "@/features/operations/sections";
import { EmptyState } from "@/components/ui";
import { useAuth } from "@/lib/auth";

/** `/operations` redirects to the first destination the current user may access. */
export function OperationsIndexRedirect(): JSX.Element {
  const { hasPermission } = useAuth();
  const first = OPERATIONS_SECTIONS.find((section) => hasPermission(section.permission));
  return first ? <Navigate to={first.path} replace /> : <Outlet />;
}

/**
 * The operations shell (Doc 05 B11.8), with destinations filtered by their existing permissions.
 */
export function OperationsPage(): JSX.Element {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const sections = OPERATIONS_SECTIONS.filter((section) => hasPermission(section.permission));
  const active = sections.find((section) =>
    location.pathname.startsWith(section.path),
  );
  const isDeveloperWorkspace = active?.key === "api";

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          {
            label: isDeveloperWorkspace ? "Developer" : "Operations",
            to: isDeveloperWorkspace ? active.path : sections[0]?.path,
          },
          ...(active ? [{ label: active.label }] : []),
        ]}
      />
      <PageHeader
        title={isDeveloperWorkspace ? "Developer Hub" : "Operations"}
        description={
          active?.description ?? "Background work, queue backlog and the health of the fleet."
        }
      />

      {sections.length === 0 ? <EmptyState title="You don't have access to this area" description="Ask an administrator if you need operational access." /> : <>
      {!isDeveloperWorkspace ? <nav aria-label="Operations sections" className="mb-5 flex gap-1 overflow-x-auto rounded-xl border border-border bg-surface-subtle p-1.5">
        {sections.map((section) => (
          <NavLink
            key={section.key}
            to={section.path}
            className={({ isActive }) =>
              `shrink-0 rounded-lg px-3 py-2 text-sm font-semibold focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus ${
                isActive
                  ? "bg-surface text-accent shadow-sm ring-1 ring-border"
                  : "text-text-secondary hover:bg-hover"
              }`
            }
          >
            {section.label}
          </NavLink>
        ))}
      </nav> : null}

      <Outlet />
      </>}
    </PageContainer>
  );
}
