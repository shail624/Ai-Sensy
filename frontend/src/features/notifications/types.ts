import type { components, operations } from "@/lib/api/schema";

export type Notification = components["schemas"]["NotificationResponse"];
export type NotificationsPage = components["schemas"]["NotificationsPage"];
export type NotificationListQuery = NonNullable<
  operations["list_notifications_api_v1_notifications_get"]["parameters"]["query"]
>;

export type NotificationSettings = components["schemas"]["NotificationSettings"];
// `muted_types` carries a server-side default, so the generated type makes it optional.
export type MutedTypes = NonNullable<NotificationSettings["muted_types"]>;
export type NotificationTypeName = MutedTypes[number];

export const NOTIFICATION_TYPES = [
  ["follow_up_due", "Follow-up due"],
  ["release_date_due", "Release date due"],
  ["case_assigned", "Assignment"],
  ["case_status_changed", "Status change"],
  ["automation_attention", "Automation"],
  ["report_ready", "Report ready"],
] as const;

export const NOTIFICATION_STATUSES = [
  ["unread", "Unread"],
  ["read", "Read"],
  ["overdue", "Overdue"],
  ["resolved", "Resolved"],
] as const;
