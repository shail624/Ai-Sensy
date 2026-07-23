import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  FeatureFlag,
  FeatureFlagPatchRequest,
  Organization,
  OrganizationUpdateRequest,
  Setting,
} from "@/features/settings/types";

// Shared error helper, re-exported for this feature's components (as the other features do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const settingsKeys = {
  all: ["settings"] as const,
  organization: ["settings", "organization"] as const,
  values: ["settings", "values"] as const,
  flags: ["settings", "flags"] as const,
  preferences: ["settings", "preferences"] as const,
};

/**
 * The organization this platform runs for.
 *
 * Single-tenant: the endpoint takes no id and always operates on the caller's own organization.
 */
export function useOrganization() {
  return useQuery({
    queryKey: settingsKeys.organization,
    queryFn: async (): Promise<Organization> => unwrap(await api.GET("/api/v1/organization")),
  });
}

/**
 * System and organization settings.
 *
 * The read returns both scopes together: system rows come from the server's own configuration and
 * organization rows from this tenant. `PUT /settings` writes **only** the organization scope, so
 * the two are presented differently — see `isEditableSetting`.
 */
export function useSettings() {
  return useQuery({
    queryKey: settingsKeys.values,
    queryFn: async (): Promise<Setting[]> => unwrap(await api.GET("/api/v1/settings")),
  });
}

/** Feature flags. Global, not per-organization — the endpoint lists them for the whole platform. */
export function useFeatureFlags() {
  return useQuery({
    queryKey: settingsKeys.flags,
    queryFn: async (): Promise<FeatureFlag[]> => unwrap(await api.GET("/api/v1/feature-flags")),
  });
}

/** The signed-in user's own preferences. Gated on `auth:self`, which every account holds. */
export function usePreferences() {
  return useQuery({
    queryKey: settingsKeys.preferences,
    queryFn: async (): Promise<Record<string, unknown>> =>
      unwrap(await api.GET("/api/v1/users/me/preferences")).preferences,
  });
}

/** Every settings write is audited, so the audit trail is invalidated alongside the value itself. */
function useSettingsMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  invalidate: readonly (readonly unknown[])[],
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      for (const key of invalidate) {
        void queryClient.invalidateQueries({ queryKey: key });
      }
      void queryClient.invalidateQueries({ queryKey: ["admin", "audit"] });
    },
  });
}

/**
 * Amend the organization.
 *
 * `row_version` rides along so a concurrent change surfaces as the server's conflict rather than
 * silently overwriting. `slug` is absent from the update model — it identifies the organization and
 * is set at creation.
 */
export function useUpdateOrganization() {
  return useSettingsMutation(
    async (body: OrganizationUpdateRequest): Promise<Organization> =>
      unwrap(await api.PATCH("/api/v1/organization", { body })),
    [settingsKeys.organization],
  );
}

/**
 * Write organization settings.
 *
 * A **partial** write: the request carries only the keys being changed, and the server upserts each
 * one. It is not a replace, so omitting a key leaves it alone rather than deleting it — which is
 * also why there is no way to remove a key through this API.
 */
export function useUpdateSettings() {
  return useSettingsMutation(
    async (values: Record<string, unknown>): Promise<Setting[]> =>
      unwrap(await api.PUT("/api/v1/settings", { body: { values } })),
    [settingsKeys.values],
  );
}

/**
 * Toggle or re-describe a feature flag.
 *
 * The endpoint **upserts**: patching a key that does not exist creates the flag rather than
 * answering 404. Only keys already present are offered here, because a flag nothing reads is a
 * value with no effect.
 */
export function useUpdateFeatureFlag() {
  return useSettingsMutation(
    async ({ key, body }: { key: string; body: FeatureFlagPatchRequest }): Promise<FeatureFlag> =>
      unwrap(
        await api.PATCH("/api/v1/feature-flags/{key}", {
          params: { path: { key } },
          body,
        }),
      ),
    [settingsKeys.flags],
  );
}

/** Partial, like the settings write: only the keys sent are upserted. */
export function useUpdatePreferences() {
  return useSettingsMutation(
    async (preferences: Record<string, unknown>): Promise<Record<string, unknown>> =>
      unwrap(await api.PUT("/api/v1/users/me/preferences", { body: { preferences } })).preferences,
    [settingsKeys.preferences],
  );
}
