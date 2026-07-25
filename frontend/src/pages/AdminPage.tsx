import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { EmptyState } from "@/components/ui";
import { ADMIN_SECTIONS } from "@/features/admin";
import { useAuth } from "@/lib/auth";

/**
 * `/admin` itself has no content — it lands on the first section this administrator can read.
 * Sending everyone to Users would give an audit-only reviewer a refusal as their first impression
 * of the area.
 */
export function AdminIndexRedirect(): JSX.Element {
  const { hasPermission } = useAuth();
  const first = ADMIN_SECTIONS.find((section) => hasPermission(section.permission));
  return first ? <Navigate to={first.path} replace /> : <Outlet />;
}

/**
 * The administration shell (Doc 05 B11) — sub-navigation plus the active section.
 *
 * Only the sections the signed-in administrator can actually read are offered. Someone who holds
 * `audit:read` and nothing else sees one tab, not four that would 403 on arrival; the routes carry
 * the same permission, so typing the URL gets the same honest answer.
 */
export function AdminPage(): JSX.Element {
  const { hasPermission } = useAuth();
  const location = useLocation();
  const sections = ADMIN_SECTIONS.filter((section) => hasPermission(section.permission));

  const active = sections.find((section) => location.pathname.startsWith(section.path));

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          { label: "Administration", to: sections[0]?.path },
          ...(active ? [{ label: active.label }] : []),
        ]}
      />
      <PageHeader
        title="Administration"
        description={active?.description ?? "Accounts, access and the record of what was done."}
      />

      {sections.length === 0 ? (
        <EmptyState
          title="You don't have access to this area"
          description="Ask an administrator if you need access."
        />
      ) : (
        <>
          <nav aria-label="Administration sections" className="mb-5 flex gap-1 overflow-x-auto rounded-xl border border-border bg-surface-subtle p-1.5">
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
          </nav>

          <Outlet />
        </>
      )}
    </PageContainer>
  );
}
