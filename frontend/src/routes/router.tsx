import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/components/layout";
import { Spinner } from "@/components/ui";
import { ApiKeysPanel, AuditPanel, RolesPanel, UsersPanel } from "@/features/admin";
import { NumberList, WabaList } from "@/features/channels";
import { JobList, QueueMonitor } from "@/features/operations";
import {
  ApplicationPanel,
  FeatureFlagsPanel,
  OrganizationPanel,
  PreferencesPanel,
} from "@/features/settings";
import { AdminIndexRedirect, AdminPage } from "@/pages/AdminPage";
import { PipelineDetailPage } from "@/pages/PipelineDetailPage";
import { PipelinesPage } from "@/pages/PipelinesPage";
import { SegmentCreatePage } from "@/pages/SegmentCreatePage";
import { SegmentDetailPage } from "@/pages/SegmentDetailPage";
import { SegmentEditPage } from "@/pages/SegmentEditPage";
import { SegmentsPage } from "@/pages/SegmentsPage";
import { SettingsIndexRedirect, SettingsPage } from "@/pages/SettingsPage";
import { JobDetailPage } from "@/pages/JobDetailPage";
import { OperationsIndexRedirect, OperationsPage } from "@/pages/OperationsPage";
import { ChannelsIndexRedirect, ChannelsPage } from "@/pages/ChannelsPage";
import { NumberDetailPage } from "@/pages/NumberDetailPage";
import { WabaDetailPage } from "@/pages/WabaDetailPage";
import { CampaignCreatePage } from "@/pages/CampaignCreatePage";
import { CampaignDetailPage } from "@/pages/CampaignDetailPage";
import { CampaignEditPage } from "@/pages/CampaignEditPage";
import { CampaignsPage } from "@/pages/CampaignsPage";
// `ComingSoonPage` is no longer routed: every destination in the navigation is now built. The
// component remains for a future unbuilt module rather than being deleted along with its tests.
import { ContactProfilePage } from "@/pages/ContactProfilePage";
import { ContactsPage } from "@/pages/ContactsPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { InboxPage } from "@/pages/InboxPage";
import { LoginPage } from "@/pages/LoginPage";
import { MediaDetailPage } from "@/pages/MediaDetailPage";
import { MediaPage } from "@/pages/MediaPage";
import { NotFound } from "@/pages/NotFound";
import { TasksPage } from "@/pages/TasksPage";
import { TemplateCreatePage } from "@/pages/TemplateCreatePage";
import { TemplateDetailPage } from "@/pages/TemplateDetailPage";
import { TemplateEditPage } from "@/pages/TemplateEditPage";
import { TemplatesPage } from "@/pages/TemplatesPage";
import { RequireAnonymous, RequireAuth, RequirePermission } from "@/routes/guards";

/**
 * Analytics is the only route that pulls in a charting library, so it is loaded on demand: the
 * chart code never reaches a user who does not open the dashboard, and the initial bundle stays
 * the size it was before Phase 8. Everything else is small enough that splitting would cost a
 * round-trip for no benefit.
 */
const AnalyticsPage = lazy(async () => ({
  default: (await import("@/pages/AnalyticsPage")).AnalyticsPage,
}));

function LazyRoute({ children }: { children: React.ReactNode }): JSX.Element {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>;
}

function RouteFallback(): JSX.Element {
  return (
    <div className="p-6">
      <Spinner label="Loading…" />
    </div>
  );
}

// Public auth routes sit outside the shell; everything else renders inside AppLayout behind
// RequireAuth, with per-module permission gates from MeResponse.permissions (Doc 05 B1 / DS-20).
export const router = createBrowserRouter([
  {
    element: <RequireAnonymous />,
    children: [{ path: "/login", element: <LoginPage /> }],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/",
        element: <AppLayout />,
        children: [
          { index: true, element: <DashboardPage /> },
          {
            path: "contacts",
            element: <RequirePermission code="contacts:read" />,
            children: [
              { index: true, element: <ContactsPage /> },
              { path: ":contactId", element: <ContactProfilePage /> },
            ],
          },
          {
            path: "tasks",
            element: <RequirePermission code="tasks:read" />,
            children: [{ index: true, element: <TasksPage /> }],
          },
          {
            path: "inbox",
            element: <RequirePermission code="inbox:read" />,
            children: [{ index: true, element: <InboxPage /> }],
          },
          {
            path: "campaigns",
            element: <RequirePermission code="campaigns:read" />,
            children: [
              { index: true, element: <CampaignsPage /> },
              // `new` and `:campaignId/edit` write, so they carry the write permission the API
              // enforces — reaching them by URL without it gets the same honest refusal the nav
              // gives, not a 403 discovered on save.
              {
                path: "new",
                element: <RequirePermission code="campaigns:write" />,
                children: [{ index: true, element: <CampaignCreatePage /> }],
              },
              { path: ":campaignId", element: <CampaignDetailPage /> },
              {
                path: ":campaignId/edit",
                element: <RequirePermission code="campaigns:write" />,
                children: [{ index: true, element: <CampaignEditPage /> }],
              },
            ],
          },
          {
            path: "templates",
            element: <RequirePermission code="templates:read" />,
            children: [
              { index: true, element: <TemplatesPage /> },
              // `new` and `:templateId/edit` write, so they carry the write permission the API
              // enforces — reaching them by URL without it gets the same honest refusal the nav
              // gives, not a 403 discovered on submit.
              {
                path: "new",
                element: <RequirePermission code="templates:write" />,
                children: [{ index: true, element: <TemplateCreatePage /> }],
              },
              { path: ":templateId", element: <TemplateDetailPage /> },
              {
                path: ":templateId/edit",
                element: <RequirePermission code="templates:write" />,
                children: [{ index: true, element: <TemplateEditPage /> }],
              },
            ],
          },
          {
            path: "media",
            element: <RequirePermission code="media:read" />,
            children: [
              { index: true, element: <MediaPage /> },
              { path: ":mediaId", element: <MediaDetailPage /> },
            ],
          },
          {
            path: "analytics",
            element: <RequirePermission code="analytics:read" />,
            children: [
              {
                index: true,
                element: (
                  <LazyRoute>
                    <AnalyticsPage />
                  </LazyRoute>
                ),
              },
            ],
          },
          {
            // Accounts and numbers share one permission — a number belongs to an account, so there
            // is no meaningful access to one without the other — hence a single gate on the shell.
            path: "channels",
            element: <RequirePermission code="waba:read" />,
            children: [
              {
                path: "",
                element: <ChannelsPage />,
                children: [
                  { index: true, element: <ChannelsIndexRedirect /> },
                  { path: "accounts", element: <WabaList /> },
                  { path: "numbers", element: <NumberList /> },
                ],
              },
              // Detail pages render their own container, so they sit outside the tabbed shell.
              { path: "accounts/:wabaId", element: <WabaDetailPage /> },
              { path: "numbers/:numberId", element: <NumberDetailPage /> },
            ],
          },
          {
            // Leads reuse the CRM permissions rather than defining their own: `contacts:read` to
            // view the configuration, `contacts:write` to change it (Doc 07 §3/§4.1).
            path: "pipelines",
            element: <RequirePermission code="contacts:read" />,
            children: [
              { index: true, element: <PipelinesPage /> },
              { path: ":pipelineId", element: <PipelineDetailPage /> },
            ],
          },
          {
            path: "segments",
            element: <RequirePermission code="segments:read" />,
            children: [
              { index: true, element: <SegmentsPage /> },
              // `new` and `:segmentId/edit` write, so they carry the write permission the API
              // enforces — reaching them by URL without it gets the same honest refusal the nav
              // gives, not a 403 discovered on save.
              {
                path: "new",
                element: <RequirePermission code="segments:write" />,
                children: [{ index: true, element: <SegmentCreatePage /> }],
              },
              { path: ":segmentId", element: <SegmentDetailPage /> },
              {
                path: ":segmentId/edit",
                element: <RequirePermission code="segments:write" />,
                children: [{ index: true, element: <SegmentEditPage /> }],
              },
            ],
          },
          {
            // Jobs and queues share one permission — a queue is only meaningful alongside the jobs
            // that flow through it — so a single gate on the shell is the whole story.
            path: "operations",
            element: <RequirePermission code="system:read" />,
            children: [
              {
                path: "",
                element: <OperationsPage />,
                children: [
                  { index: true, element: <OperationsIndexRedirect /> },
                  { path: "jobs", element: <JobList /> },
                  { path: "queues", element: <QueueMonitor /> },
                ],
              },
              // The detail page renders its own container, so it sits outside the tabbed shell.
              { path: "jobs/:jobId", element: <JobDetailPage /> },
            ],
          },
          {
            // Each section carries the permission its own endpoints enforce, so reaching one by
            // URL without it gets the same honest refusal the sub-navigation gives.
            path: "admin",
            element: <AdminPage />,
            children: [
              { index: true, element: <AdminIndexRedirect /> },
              {
                path: "users",
                element: <RequirePermission code="users:read" />,
                children: [{ index: true, element: <UsersPanel /> }],
              },
              {
                path: "roles",
                element: <RequirePermission code="roles:read" />,
                children: [{ index: true, element: <RolesPanel /> }],
              },
              {
                path: "api-keys",
                element: <RequirePermission code="apikeys:manage" />,
                children: [{ index: true, element: <ApiKeysPanel /> }],
              },
              {
                path: "audit",
                element: <RequirePermission code="audit:read" />,
                children: [{ index: true, element: <AuditPanel /> }],
              },
            ],
          },
          {
            // Each section carries the permission its own endpoints enforce. Preferences is on
            // `auth:self` rather than `settings:read`, so someone with no administrative access
            // still reaches their own record.
            path: "settings",
            element: <SettingsPage />,
            children: [
              { index: true, element: <SettingsIndexRedirect /> },
              {
                path: "organization",
                element: <RequirePermission code="settings:read" />,
                children: [{ index: true, element: <OrganizationPanel /> }],
              },
              {
                path: "application",
                element: <RequirePermission code="settings:read" />,
                children: [{ index: true, element: <ApplicationPanel /> }],
              },
              {
                path: "flags",
                element: <RequirePermission code="settings:read" />,
                children: [{ index: true, element: <FeatureFlagsPanel /> }],
              },
              {
                path: "preferences",
                element: <RequirePermission code="auth:self" />,
                children: [{ index: true, element: <PreferencesPanel /> }],
              },
            ],
          },
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
]);
