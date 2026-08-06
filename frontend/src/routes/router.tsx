import { lazy, Suspense, type ComponentType, type ElementType, type LazyExoticComponent, type ReactNode } from "react";
import { createBrowserRouter } from "react-router-dom";

import { AppLayout } from "@/components/layout";
import { Spinner } from "@/components/ui";
import { OPERATIONS_PERMISSIONS } from "@/features/operations";
import { LoginPage } from "@/pages/LoginPage";
import { NotFound } from "@/pages/NotFound";
import { RequireAnonymous, RequireAnyPermission, RequireAuth, RequirePermission } from "@/routes/guards";

type RouteComponent = ComponentType<Record<string, never>>;

function lazyNamed(
  loader: () => Promise<Record<string, unknown>>,
  exportName: string,
): LazyExoticComponent<RouteComponent> {
  return lazy(async () => ({
    default: (await loader())[exportName] as RouteComponent,
  }));
}

function lazyElement(Component: ElementType): JSX.Element {
  return (
    <LazyRoute>
      <Component />
    </LazyRoute>
  );
}

const AdminIndexRedirect = lazyNamed(() => import("@/pages/AdminPage"), "AdminIndexRedirect");
const AdminPage = lazyNamed(() => import("@/pages/AdminPage"), "AdminPage");
const AnalyticsPage = lazyNamed(() => import("@/pages/AnalyticsPage"), "AnalyticsPage");
const AutomationPage = lazyNamed(() => import("@/pages/AutomationPage"), "AutomationPage");
const BroadcastsPage = lazyNamed(() => import("@/pages/BroadcastsPage"), "BroadcastsPage");
const CampaignCreatePage = lazyNamed(() => import("@/pages/CampaignCreatePage"), "CampaignCreatePage");
const CampaignDetailPage = lazyNamed(() => import("@/pages/CampaignDetailPage"), "CampaignDetailPage");
const CampaignEditPage = lazyNamed(() => import("@/pages/CampaignEditPage"), "CampaignEditPage");
const CampaignsPage = lazyNamed(() => import("@/pages/CampaignsPage"), "CampaignsPage");
const ChannelsIndexRedirect = lazyNamed(() => import("@/pages/ChannelsPage"), "ChannelsIndexRedirect");
const ChannelsPage = lazyNamed(() => import("@/pages/ChannelsPage"), "ChannelsPage");
const ContactProfilePage = lazyNamed(() => import("@/pages/ContactProfilePage"), "ContactProfilePage");
const ContactsPage = lazyNamed(() => import("@/pages/ContactsPage"), "ContactsPage");
const DashboardPage = lazyNamed(() => import("@/pages/DashboardPage"), "DashboardPage");
const InboxPage = lazyNamed(() => import("@/pages/InboxPage"), "InboxPage");
const JobDetailPage = lazyNamed(() => import("@/pages/JobDetailPage"), "JobDetailPage");
const MediaDetailPage = lazyNamed(() => import("@/pages/MediaDetailPage"), "MediaDetailPage");
const MediaPage = lazyNamed(() => import("@/pages/MediaPage"), "MediaPage");
const NumberDetailPage = lazyNamed(() => import("@/pages/NumberDetailPage"), "NumberDetailPage");
const OperationsIndexRedirect = lazyNamed(() => import("@/pages/OperationsPage"), "OperationsIndexRedirect");
const OperationsPage = lazyNamed(() => import("@/pages/OperationsPage"), "OperationsPage");
const PipelineDetailPage = lazyNamed(() => import("@/pages/PipelineDetailPage"), "PipelineDetailPage");
const PipelinesPage = lazyNamed(() => import("@/pages/PipelinesPage"), "PipelinesPage");
const ReactivationOverview = lazyNamed(() => import("@/pages/ReactivationPage"), "ReactivationOverview");
const ReactivationPage = lazyNamed(() => import("@/pages/ReactivationPage"), "ReactivationPage");
const ReactivationWorkspace = lazyNamed(() => import("@/pages/ReactivationPage"), "ReactivationWorkspace");
const ScanPage = lazyNamed(() => import("@/pages/ScanPage"), "ScanPage");
const SegmentCreatePage = lazyNamed(() => import("@/pages/SegmentCreatePage"), "SegmentCreatePage");
const SegmentDetailPage = lazyNamed(() => import("@/pages/SegmentDetailPage"), "SegmentDetailPage");
const SegmentEditPage = lazyNamed(() => import("@/pages/SegmentEditPage"), "SegmentEditPage");
const SegmentsPage = lazyNamed(() => import("@/pages/SegmentsPage"), "SegmentsPage");
const SettingsIndexRedirect = lazyNamed(() => import("@/pages/SettingsPage"), "SettingsIndexRedirect");
const SettingsPage = lazyNamed(() => import("@/pages/SettingsPage"), "SettingsPage");
const TasksPage = lazyNamed(() => import("@/pages/TasksPage"), "TasksPage");
const TemplateCreatePage = lazyNamed(() => import("@/pages/TemplateCreatePage"), "TemplateCreatePage");
const TemplateDetailPage = lazyNamed(() => import("@/pages/TemplateDetailPage"), "TemplateDetailPage");
const TemplateEditPage = lazyNamed(() => import("@/pages/TemplateEditPage"), "TemplateEditPage");
const TemplatesPage = lazyNamed(() => import("@/pages/TemplatesPage"), "TemplatesPage");
const WabaDetailPage = lazyNamed(() => import("@/pages/WabaDetailPage"), "WabaDetailPage");

const ApiKeysPanel = lazyNamed(() => import("@/features/admin"), "ApiKeysPanel");
const AuditPanel = lazyNamed(() => import("@/features/admin"), "AuditPanel");
const PermissionsPanel = lazyNamed(() => import("@/features/admin"), "PermissionsPanel");
const RolesPanel = lazyNamed(() => import("@/features/admin"), "RolesPanel");
const UsersPanel = lazyNamed(() => import("@/features/admin"), "UsersPanel");
const NumberList = lazyNamed(() => import("@/features/channels"), "NumberList");
const WabaList = lazyNamed(() => import("@/features/channels"), "WabaList");
const JobList = lazyNamed(() => import("@/features/operations"), "JobList");
const LogsPanel = lazyNamed(() => import("@/features/operations"), "LogsPanel");
const OperationsOverview = lazyNamed(() => import("@/features/operations"), "OperationsOverview");
const QueueMonitor = lazyNamed(() => import("@/features/operations"), "QueueMonitor");
const SystemHealthPanel = lazyNamed(() => import("@/features/operations"), "SystemHealthPanel");
const WebhooksPanel = lazyNamed(() => import("@/features/operations"), "WebhooksPanel");
const ApplicationPanel = lazyNamed(() => import("@/features/settings"), "ApplicationPanel");
const FeatureFlagsPanel = lazyNamed(() => import("@/features/settings"), "FeatureFlagsPanel");
const OrganizationPanel = lazyNamed(() => import("@/features/settings"), "OrganizationPanel");
const PreferencesPanel = lazyNamed(() => import("@/features/settings"), "PreferencesPanel");
const TagsPanel = lazyNamed(() => import("@/features/settings"), "TagsPanel");
const CannedMessagesPanel = lazyNamed(() => import("@/features/settings"), "CannedMessagesPanel");
const UserAttributesPanel = lazyNamed(() => import("@/features/settings"), "UserAttributesPanel");

function LazyRoute({ children }: { children: ReactNode }): JSX.Element {
  return <Suspense fallback={<RouteFallback />}>{children}</Suspense>;
}

function RouteFallback(): JSX.Element {
  return (
    <div className="p-6" role="status" aria-live="polite">
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
          { index: true, element: lazyElement(DashboardPage) },
          {
            path: "contacts",
            element: <RequirePermission code="contacts:read" />,
            children: [
              { index: true, element: lazyElement(ContactsPage) },
              { path: ":contactId", element: lazyElement(ContactProfilePage) },
            ],
          },
          {
            path: "tasks",
            element: <RequirePermission code="tasks:read" />,
            children: [{ index: true, element: lazyElement(TasksPage) }],
          },
          {
            path: "inbox",
            element: <RequirePermission code="inbox:read" />,
            children: [{ index: true, element: lazyElement(InboxPage) }],
          },
          {
            path: "campaigns",
            element: <RequirePermission code="campaigns:read" />,
            children: [
              { index: true, element: lazyElement(CampaignsPage) },
              // `new` and `:campaignId/edit` write, so they carry the write permission the API
              // enforces — reaching them by URL without it gets the same honest refusal the nav
              // gives, not a 403 discovered on save.
              {
                path: "new",
                element: <RequirePermission code="campaigns:write" />,
                children: [{ index: true, element: lazyElement(CampaignCreatePage) }],
              },
              { path: ":campaignId", element: lazyElement(CampaignDetailPage) },
              {
                path: ":campaignId/edit",
                element: <RequirePermission code="campaigns:write" />,
                children: [{ index: true, element: lazyElement(CampaignEditPage) }],
              },
            ],
          },
          {
            path: "broadcasts",
            element: <RequirePermission code="campaigns:read" />,
            children: [{ index: true, element: lazyElement(BroadcastsPage) }],
          },
          {
            path: "templates",
            element: <RequirePermission code="templates:read" />,
            children: [
              { index: true, element: lazyElement(TemplatesPage) },
              // `new` and `:templateId/edit` write, so they carry the write permission the API
              // enforces — reaching them by URL without it gets the same honest refusal the nav
              // gives, not a 403 discovered on submit.
              {
                path: "new",
                element: <RequirePermission code="templates:write" />,
                children: [{ index: true, element: lazyElement(TemplateCreatePage) }],
              },
              { path: ":templateId", element: lazyElement(TemplateDetailPage) },
              {
                path: ":templateId/edit",
                element: <RequirePermission code="templates:write" />,
                children: [{ index: true, element: lazyElement(TemplateEditPage) }],
              },
            ],
          },
          {
            path: "media",
            element: <RequirePermission code="media:read" />,
            children: [
              { index: true, element: lazyElement(MediaPage) },
              { path: ":mediaId", element: lazyElement(MediaDetailPage) },
            ],
          },
          {
            path: "analytics",
            element: <RequirePermission code="analytics:read" />,
            children: [
              {
                index: true,
                element: lazyElement(AnalyticsPage),
              },
            ],
          },
          {
            path: "automation",
            element: <RequirePermission code="automations:read" />,
            children: [{ index: true, element: lazyElement(AutomationPage) }],
          },
          {
            path: "reactivation",
            element: <RequirePermission code="reactivation:read" />,
            children: [
              {
                path: "",
                element: lazyElement(ReactivationPage),
                children: [
                  { index: true, element: lazyElement(ReactivationOverview) },
                  { path: "eligible", element: lazyElement(ReactivationWorkspace) },
                  { path: "bulk-eligibility", element: lazyElement(ReactivationWorkspace) },
                  { path: "interested", element: lazyElement(ReactivationWorkspace) },
                  { path: "pipeline", element: lazyElement(ReactivationWorkspace) },
                  { path: "kyc", element: <RequirePermission code="kyc:read">{lazyElement(ReactivationWorkspace)}</RequirePermission> },
                  { path: "documents", element: <RequirePermission code="documents:read">{lazyElement(ReactivationWorkspace)}</RequirePermission> },
                  { path: "sim-orders", element: lazyElement(ReactivationWorkspace) },
                  { path: "activation", element: lazyElement(ReactivationWorkspace) },
                  { path: "completed", element: lazyElement(ReactivationWorkspace) },
                  { path: "reports", element: <RequirePermission code="analytics:read">{lazyElement(ReactivationWorkspace)}</RequirePermission> },
                ],
              },
            ],
          },
          {
            path: "scan",
            element: <RequirePermission code="contacts:read" />,
            children: [{ index: true, element: lazyElement(ScanPage) }],
          },
          {
            // Accounts and numbers share one permission — a number belongs to an account, so there
            // is no meaningful access to one without the other — hence a single gate on the shell.
            path: "channels",
            element: <RequirePermission code="waba:read" />,
            children: [
              {
                path: "",
                element: lazyElement(ChannelsPage),
                children: [
                  { index: true, element: lazyElement(ChannelsIndexRedirect) },
                  { path: "accounts", element: lazyElement(WabaList) },
                  { path: "numbers", element: lazyElement(NumberList) },
                ],
              },
              // Detail pages render their own container, so they sit outside the tabbed shell.
              { path: "accounts/:wabaId", element: lazyElement(WabaDetailPage) },
              { path: "numbers/:numberId", element: lazyElement(NumberDetailPage) },
            ],
          },
          {
            // Leads reuse the CRM permissions rather than defining their own: `contacts:read` to
            // view the configuration, `contacts:write` to change it (Doc 07 §3/§4.1).
            path: "pipelines",
            element: <RequirePermission code="contacts:read" />,
            children: [
              { index: true, element: lazyElement(PipelinesPage) },
              { path: ":pipelineId", element: lazyElement(PipelineDetailPage) },
            ],
          },
          {
            path: "segments",
            element: <RequirePermission code="segments:read" />,
            children: [
              { index: true, element: lazyElement(SegmentsPage) },
              // `new` and `:segmentId/edit` write, so they carry the write permission the API
              // enforces — reaching them by URL without it gets the same honest refusal the nav
              // gives, not a 403 discovered on save.
              {
                path: "new",
                element: <RequirePermission code="segments:write" />,
                children: [{ index: true, element: lazyElement(SegmentCreatePage) }],
              },
              { path: ":segmentId", element: lazyElement(SegmentDetailPage) },
              {
                path: ":segmentId/edit",
                element: <RequirePermission code="segments:write" />,
                children: [{ index: true, element: lazyElement(SegmentEditPage) }],
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
                element: lazyElement(OperationsPage),
                children: [
                  { index: true, element: lazyElement(OperationsIndexRedirect) },
                  { path: "overview", element: <RequirePermission code="system:read">{lazyElement(OperationsOverview)}</RequirePermission> },
                  { path: "jobs", element: <RequirePermission code="system:read">{lazyElement(JobList)}</RequirePermission> },
                  { path: "queues", element: <RequirePermission code="system:read">{lazyElement(QueueMonitor)}</RequirePermission> },
                  { path: "health", element: <RequirePermission code="system:read">{lazyElement(SystemHealthPanel)}</RequirePermission> },
                  { path: "logs", element: <RequirePermission code="system:read">{lazyElement(LogsPanel)}</RequirePermission> },
                  { path: "api", element: <RequirePermission code="apikeys:manage">{lazyElement(ApiKeysPanel)}</RequirePermission> },
                  { path: "webhooks", element: <RequirePermission code="waba:read">{lazyElement(WebhooksPanel)}</RequirePermission> },
                ],
              },
              // The detail page renders its own container, so it sits outside the tabbed shell.
              { path: "jobs/:jobId", element: lazyElement(JobDetailPage) },
            ],
          },
          {
            // Each section carries the permission its own endpoints enforce, so reaching one by
            // URL without it gets the same honest refusal the sub-navigation gives.
            path: "admin",
            element: lazyElement(AdminPage),
            children: [
              { index: true, element: lazyElement(AdminIndexRedirect) },
              {
                path: "users",
                element: <RequirePermission code="users:read" />,
                children: [{ index: true, element: lazyElement(UsersPanel) }],
              },
              {
                path: "roles",
                element: <RequirePermission code="roles:read" />,
                children: [{ index: true, element: lazyElement(RolesPanel) }],
              },
              {
                path: "permissions",
                element: <RequirePermission code="roles:read" />,
                children: [{ index: true, element: lazyElement(PermissionsPanel) }],
              },
              {
                path: "api-keys",
                element: <RequirePermission code="apikeys:manage" />,
                children: [{ index: true, element: lazyElement(ApiKeysPanel) }],
              },
              {
                path: "audit",
                element: <RequirePermission code="audit:read" />,
                children: [{ index: true, element: lazyElement(AuditPanel) }],
              },
            ],
          },
          {
            // Each section carries the permission its own endpoints enforce. Preferences is on
            // `auth:self` rather than `settings:read`, so someone with no administrative access
            // still reaches their own record.
            path: "settings",
            element: lazyElement(SettingsPage),
            children: [
              { index: true, element: lazyElement(SettingsIndexRedirect) },
              {
                path: "organization",
                element: <RequirePermission code="settings:read" />,
                children: [{ index: true, element: lazyElement(OrganizationPanel) }],
              },
              {
                path: "application",
                element: <RequirePermission code="settings:read" />,
                children: [{ index: true, element: lazyElement(ApplicationPanel) }],
              },
              {
                path: "flags",
                element: <RequirePermission code="settings:read" />,
                children: [{ index: true, element: lazyElement(FeatureFlagsPanel) }],
              },
              {
                path: "tags",
                element: <RequirePermission code="contacts:read" />,
                children: [{ index: true, element: lazyElement(TagsPanel) }],
              },
              {
                path: "canned-messages",
                element: <RequirePermission code="inbox:read" />,
                children: [{ index: true, element: lazyElement(CannedMessagesPanel) }],
              },
              {
                path: "user-attributes",
                element: <RequirePermission code="contacts:read" />,
                children: [{ index: true, element: lazyElement(UserAttributesPanel) }],
              },
              {
                path: "preferences",
                element: <RequirePermission code="auth:self" />,
                children: [{ index: true, element: lazyElement(PreferencesPanel) }],
              },
            ],
          },
          { path: "*", element: <NotFound /> },
        ],
      },
    ],
  },
]);
