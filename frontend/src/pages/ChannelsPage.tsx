import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { CHANNEL_SECTIONS } from "@/features/channels";

/** `/channels` has no content of its own — accounts are the way in. */
export function ChannelsIndexRedirect(): JSX.Element {
  return <Navigate to="/channels/accounts" replace />;
}

/**
 * The channel-management shell (Doc 05 B11.5/B11.6) — accounts and numbers under one header.
 *
 * Both sections sit behind `waba:read`, so unlike Administration there is nothing per-tab to gate:
 * a user who can reach this page can reach both halves of it.
 */
export function ChannelsPage(): JSX.Element {
  const location = useLocation();
  const active = CHANNEL_SECTIONS.find((section) =>
    location.pathname.startsWith(section.path),
  );

  return (
    <PageContainer>
      <Breadcrumbs
        items={[
          { label: "Dashboard", to: "/" },
          { label: "WhatsApp", to: "/channels/accounts" },
          ...(active ? [{ label: active.label }] : []),
        ]}
      />
      <PageHeader
        title="WhatsApp"
        description={
          active?.description ??
          "Connected accounts, their phone numbers, and the health of both."
        }
      />

      <nav aria-label="Channel sections" className="mb-4 flex flex-wrap gap-2">
        {CHANNEL_SECTIONS.map((section) => (
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
