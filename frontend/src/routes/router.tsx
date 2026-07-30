import { lazy, Suspense } from "react";
import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/components/layout";
import { Spinner } from "@/components/ui";
import { ApiKeysPanel, AuditPanel, PermissionsPanel, RolesPanel, UsersPanel } from "@/features/admin";
import { NumberList, WabaList } from "@/features/channels";
import {
  JobList,
  LogsPanel,
  OPERATIONS_PERMISSIONS,
  OperationsOverview,
  QueueMonitor,
  SystemHealthPanel,
  WebhooksPanel,
} from "@/features/operations";
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
import { BroadcastsPage } from "@/pages/BroadcastsPage";
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
import { RequireAnonymous, RequireAnyPermission, RequireAuth, RequirePermission } from "@/routes/guards";

/** Heavy analytics and Phase 3 workspace routes load only when opened. */
const AnalyticsPage = lazy(async () => ({
  default: (await import("@/pages/AnalyticsPage")).AnalyticsPage,
}));
const AutomationPage = lazy(async () => ({ default: (await import("@/pages/AutomationPage")).AutomationPage }));
const ReactivationPage = lazy(async () => ({ default: (await import("@/pages/ReactivationPage")).ReactivationPage }));
const ReactivationOverview = lazy(async () => ({ default: (await import("@/pages/ReactivationPage")).ReactivationOverview }));
const ReactivationWorkspace = lazy(async () => ({ default: (await import("@/pages/ReactivationPage")).ReactivationWorkspace }));
const ScanPage = lazy(async () => ({ default: (await import("@/pages/ScanPage")).ScanPage }));

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
            path: "broadcasts",
            element: <RequirePermission code="campaigns:read" />,
            children: [{ index: true, element: <BroadcastsPage /> }],
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
            path: "automation",
            element: <RequirePermission code="automations:read" />,
            children: [{ index: true, element: <LazyRoute><AutomationPage /></LazyRoute> }],
          },
          {
            path: "reactivation",
            element: <RequirePermission code="contacts:read" />,
            children: [
              {
                path: "",
                element: <LazyRoute><ReactivationPage /></LazyRoute>,
                children: [
                  { index: true, element: <LazyRoute><ReactivationOverview /></LazyRoute> },
                  { path: "eligible", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "bulk-eligibility", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "interested", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "pipeline", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "kyc", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "documents", element: <RequirePermission code="documents:read"><LazyRoute><ReactivationWorkspace /></LazyRoute></RequirePermission> },
                  { path: "sim-orders", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "activation", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "completed", element: <LazyRoute><ReactivationWorkspace /></LazyRoute> },
                  { path: "reports", element: <RequirePermission code="analytics:read"><LazyRoute><ReactivationWorkspace /></LazyRoute></RequirePermission> },
                ],
              },
            ],
          },
          {
            path: "scan",
            element: <RequirePermission code="contacts:read" />,
            children: [{ index: true, element: <LazyRoute><ScanPage /></LazyRoute> }],
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
            // The shell accepts any operations permission; each destination keeps its own guard.
            path: "operations",
            element: <RequireAnyPermission codes={OPERATIONS_PERMISSIONS} />,
            children: [
              {
                path: "",
                element: <OperationsPage />,
                children: [
                  { index: true, element: <OperationsIndexRedirect /> },
                  { path: "overview", element: <RequirePermission code="system:read"><OperationsOverview /></RequirePermission> },
                  { path: "jobs", element: <RequirePermission code="system:read"><JobList /></RequirePermission> },
                  { path: "queues", element: <RequirePermission code="system:read"><QueueMonitor /></RequirePermission> },
                  { path: "health", element: <RequirePermission code="system:read"><SystemHealthPanel /></RequirePermission> },
                  { path: "logs", element: <RequirePermission code="system:read"><LogsPanel /></RequirePermission> },
                  { path: "api", element: <RequirePermission code="apikeys:manage"><ApiKeysPanel /></RequirePermission> },
                  { path: "webhooks", element: <RequirePermission code="waba:read"><WebhooksPanel /></RequirePermission> },
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
                path: "permissions",
                element: <RequirePermission code="roles:read" />,
                children: [{ index: true, element: <PermissionsPanel /> }],
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
