import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type { NotificationListQuery, NotificationsPage } from "@/features/notifications/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export const notificationKeys = {
  all: ["notifications"] as const,
  list: (query: NotificationListQuery) => ["notifications", "list", query] as const,
  unread: ["notifications", "unread"] as const,
};

export function useNotifications(query: NotificationListQuery, enabled = true) {
  return useQuery({
    queryKey: notificationKeys.list(query),
    queryFn: async (): Promise<NotificationsPage> =>
      unwrap(await api.GET("/api/v1/notifications", { params: { query } })),
    placeholderData: keepPreviousData,
    enabled,
    refetchInterval: 15_000,
  });
}

export function useUnreadCount(enabled = true) {
  return useQuery({
    queryKey: notificationKeys.unread,
    queryFn: async () => unwrap(await api.GET("/api/v1/notifications/unread-count")),
    enabled,
    refetchInterval: 15_000,
  });
}

function useReadMutation<T>(mutationFn: (value: T) => Promise<unknown>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => void client.invalidateQueries({ queryKey: notificationKeys.all }),
  });
}

export function useMarkNotificationRead() {
  return useReadMutation(async (id: string) =>
    unwrap(
      await api.POST("/api/v1/notifications/{notification_id}/read", {
        params: { path: { notification_id: id } },
      }),
    ),
  );
}

export function useMarkAllNotificationsRead() {
  return useReadMutation(async () => unwrap(await api.POST("/api/v1/notifications/read-all")));
}
