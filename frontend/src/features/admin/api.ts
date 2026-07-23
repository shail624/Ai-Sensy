import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  ApiKey,
  ApiKeyCreateRequest,
  ApiKeyCreated,
  AuditEntry,
  Permission,
  Role,
  RoleCreateRequest,
  RoleUpdateRequest,
  User,
  UserCreateRequest,
  UserUpdateRequest,
} from "@/features/admin/types";

// Shared error helper, re-exported for this feature's components (as the other features do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const adminKeys = {
  users: ["admin", "users"] as const,
  user: (id: string) => ["admin", "users", id] as const,
  roles: ["admin", "roles"] as const,
  permissions: ["admin", "permissions"] as const,
  apiKeys: ["admin", "api-keys"] as const,
  audit: ["admin", "audit"] as const,
};

// --- Users --------------------------------------------------------------------------------------

/**
 * The organization's users.
 *
 * `GET /users` is cursor-paginated and accepts `q`, `filter[is_active][bool]`, `filter[role][eq]`,
 * `limit` and `cursor` — but reads every one off `request.query_params`, so none is declared in the
 * contract or reachable from the generated client. It therefore answers with its **default page of
 * 50**, plus the true `page.total`. Search, filtering, sorting and paging run in the client over
 * that page (`selectors.ts`), and the UI says so when `total` exceeds what it holds.
 */
export function useUsers() {
  return useQuery({
    queryKey: adminKeys.users,
    queryFn: async () => unwrap(await api.GET("/api/v1/users")),
    placeholderData: keepPreviousData,
  });
}

/**
 * An administrative write, plus the caches it invalidates.
 *
 * Every one of these is audited, so the audit key is invalidated alongside the resource's own —
 * an admin who changes something and switches to the trail should see their action there.
 */
function useAdminMutation<TVariables, TData>(
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
    },
  });
}

export function useCreateUser() {
  return useAdminMutation(
    async (body: UserCreateRequest): Promise<User> =>
      unwrap(await api.POST("/api/v1/users", { body })),
    [adminKeys.users, adminKeys.audit],
  );
}

export function useUpdateUser() {
  return useAdminMutation(
    async ({ userId, body }: { userId: string; body: UserUpdateRequest }): Promise<User> =>
      unwrap(
        await api.PATCH("/api/v1/users/{user_id}", {
          params: { path: { user_id: userId } },
          body,
        }),
      ),
    [adminKeys.users, adminKeys.audit],
  );
}

/**
 * Enable or disable an account.
 *
 * Deactivating **revokes the user's sessions** as well as blocking sign-in, so it is the real
 * containment action — not a cosmetic flag.
 */
export function useSetUserActive() {
  return useAdminMutation(
    async ({ userId, active }: { userId: string; active: boolean }): Promise<User> => {
      const params = { path: { user_id: userId } };
      return unwrap(
        active
          ? await api.POST("/api/v1/users/{user_id}/activate", { params })
          : await api.POST("/api/v1/users/{user_id}/deactivate", { params }),
      );
    },
    [adminKeys.users, adminKeys.audit],
  );
}

export function useDeleteUser() {
  return useAdminMutation(
    async (userId: string): Promise<void> => {
      const { error } = await api.DELETE("/api/v1/users/{user_id}", {
        params: { path: { user_id: userId } },
      });
      if (error !== undefined) throw error;
    },
    [adminKeys.users, adminKeys.audit],
  );
}

// --- Roles & permissions -------------------------------------------------------------------------

export function useRoles() {
  return useQuery({
    queryKey: adminKeys.roles,
    queryFn: async (): Promise<Role[]> => unwrap(await api.GET("/api/v1/roles")),
  });
}

/** The seeded permission catalog — the vocabulary every role is built from (Doc 04 §4.3). */
export function usePermissions() {
  return useQuery({
    queryKey: adminKeys.permissions,
    queryFn: async (): Promise<Permission[]> => unwrap(await api.GET("/api/v1/permissions")),
    // The catalog only changes when a migration adds a permission, so it is not re-fetched
    // on every mount of the matrix.
    staleTime: 5 * 60_000,
  });
}

export function useCreateRole() {
  return useAdminMutation(
    async (body: RoleCreateRequest): Promise<Role> =>
      unwrap(await api.POST("/api/v1/roles", { body })),
    [adminKeys.roles, adminKeys.audit],
  );
}

/** Renames and re-describes a role. Its permission set is replaced separately, by `PUT`. */
export function useUpdateRole() {
  return useAdminMutation(
    async ({ roleId, body }: { roleId: string; body: RoleUpdateRequest }): Promise<Role> =>
      unwrap(
        await api.PATCH("/api/v1/roles/{role_id}", {
          params: { path: { role_id: roleId } },
          body,
        }),
      ),
    [adminKeys.roles, adminKeys.audit],
  );
}

/**
 * Replace a role's permission set.
 *
 * A `PUT` of the whole set, not a patch of deltas: the request states what the role should end up
 * with, so two admins editing concurrently cannot merge into a set neither of them chose.
 */
export function useSetRolePermissions() {
  return useAdminMutation(
    async ({ roleId, permissions }: { roleId: string; permissions: string[] }): Promise<Role> =>
      unwrap(
        await api.PUT("/api/v1/roles/{role_id}/permissions", {
          params: { path: { role_id: roleId } },
          body: { permissions },
        }),
      ),
    [adminKeys.roles, adminKeys.users, adminKeys.audit],
  );
}

/** Refused for a system role, and for one still assigned to a user — the server answers 409. */
export function useDeleteRole() {
  return useAdminMutation(
    async (roleId: string): Promise<void> => {
      const { error } = await api.DELETE("/api/v1/roles/{role_id}", {
        params: { path: { role_id: roleId } },
      });
      if (error !== undefined) throw error;
    },
    [adminKeys.roles, adminKeys.audit],
  );
}

// --- API keys -------------------------------------------------------------------------------------

export function useApiKeys() {
  return useQuery({
    queryKey: adminKeys.apiKeys,
    queryFn: async (): Promise<ApiKey[]> => unwrap(await api.GET("/api/v1/api-keys")),
  });
}

/**
 * Create a key. **The secret comes back exactly once** — only its hash and prefix are stored — so
 * the caller must show it immediately and cannot re-read it later.
 */
export function useCreateApiKey() {
  return useAdminMutation(
    async (body: ApiKeyCreateRequest): Promise<ApiKeyCreated> =>
      unwrap(await api.POST("/api/v1/api-keys", { body })),
    [adminKeys.apiKeys, adminKeys.audit],
  );
}

export function useRevokeApiKey() {
  return useAdminMutation(
    async (keyId: string): Promise<void> => {
      const { error } = await api.DELETE("/api/v1/api-keys/{key_id}", {
        params: { path: { key_id: keyId } },
      });
      if (error !== undefined) throw error;
    },
    [adminKeys.apiKeys, adminKeys.audit],
  );
}

export interface RotateResult {
  created: ApiKeyCreated;
  /** False when the old key could not be revoked — the new one still exists and is usable. */
  revoked: boolean;
}

/**
 * Rotate a key: issue a replacement, then revoke the original.
 *
 * There is no rotate endpoint, and composing it in this order is the point — the new secret exists
 * before the old one stops working, so an integration can be updated without a window in which
 * neither key is valid. If the revoke fails, the caller is told: two live keys is a state an
 * operator must know about, not one to paper over.
 */
export function useRotateApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      previous,
      body,
    }: {
      previous: ApiKey;
      body: ApiKeyCreateRequest;
    }): Promise<RotateResult> => {
      const created = unwrap(await api.POST("/api/v1/api-keys", { body }));
      const { error } = await api.DELETE("/api/v1/api-keys/{key_id}", {
        params: { path: { key_id: previous.id } },
      });
      return { created, revoked: error === undefined };
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: adminKeys.apiKeys });
      void queryClient.invalidateQueries({ queryKey: adminKeys.audit });
    },
  });
}

// --- Audit ----------------------------------------------------------------------------------------

/**
 * The audit trail.
 *
 * As with users, `GET /audit-logs` accepts actor/entity/action/date filters and a cursor but
 * declares none of them, so this reads the default page of 50 most recent entries and filters
 * within it. The trail is append-only and immutable, so a page of it never changes underneath the
 * reader.
 */
export function useAuditLog() {
  return useQuery({
    queryKey: adminKeys.audit,
    queryFn: async () => unwrap(await api.GET("/api/v1/audit-logs")),
    placeholderData: keepPreviousData,
  });
}

export type { AuditEntry };
