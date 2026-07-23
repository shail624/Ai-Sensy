import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { OPERATIONS_SECTIONS } from "@/features/operations";

/** `/operations` has no content of its own — the job list is the way in. */
export function OperationsIndexRedirect(): JSX.Element {
  return <Navigate to="/operations/jobs" replace />;
}

/**
 * The operations shell (Doc 05 B11.8) — jobs and queues under one header.
 *
 * Both sections sit behind `system:read`, so unlike Administration there is nothing per-tab to
 * gate: a user who can reach this page can reach both halves of it.
 */
export function OperationsPage(): JSX.Element {
  const location = useLocation();
  const active = OPERATIONS_SECTIONS.find((section) =>
    location.pathname.startsWith(section.path),
  );

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          { label: "Operations", to: "/operations/jobs" },
          ...(active ? [{ label: active.label }] : []),
        ]}
      />
      <PageHeader
        title="Operations"
        description={
          active?.description ?? "Background work, queue backlog and the health of the fleet."
        }
      />

      <nav aria-label="Operations sections" className="mb-4 flex flex-wrap gap-2">
        {OPERATIONS_SECTIONS.map((section) => (
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
    </PageContainer>
  );
}
