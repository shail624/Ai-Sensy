import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type {
  AttributeDefinition,
  Contact,
  ContactEvent,
  Tag,
} from "@/features/customer-profile/types";

// Shared error helper, re-exported for this feature's sections.
export { apiErrorMessage } from "@/lib/api/errors";

export const contactKeys = {
  detail: (id: string) => ["contact", id] as const,
  timeline: (id: string) => ["contact", id, "timeline"] as const,
  attributeDefinitions: ["custom-attributes"] as const,
  tags: ["tags"] as const,
};

export function useContact(contactId: string) {
  return useQuery({
    queryKey: contactKeys.detail(contactId),
    queryFn: async (): Promise<Contact> =>
      unwrap(
        await api.GET("/api/v1/contacts/{contact_id}", {
          params: { path: { contact_id: contactId } },
        }),
      ),
  });
}

export function useContactTimeline(contactId: string) {
  return useQuery({
    queryKey: contactKeys.timeline(contactId),
    queryFn: async (): Promise<ContactEvent[]> =>
      unwrap(
        await api.GET("/api/v1/contacts/{contact_id}/timeline", {
          params: { path: { contact_id: contactId } },
        }),
      ).data,
  });
}

export function useCustomAttributeDefinitions() {
  return useQuery({
    queryKey: contactKeys.attributeDefinitions,
    queryFn: async (): Promise<AttributeDefinition[]> =>
      unwrap(await api.GET("/api/v1/custom-attributes")),
  });
}

export function useTags() {
  return useQuery({
    queryKey: contactKeys.tags,
    queryFn: async (): Promise<Tag[]> => unwrap(await api.GET("/api/v1/tags")),
  });
}

export function useAddContactTags(contactId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tagIds: string[]): Promise<Contact> =>
      unwrap(
        await api.POST("/api/v1/contacts/{contact_id}/tags", {
          params: { path: { contact_id: contactId } },
          body: { tags: tagIds },
        }),
      ),
    onSuccess: (contact) => {
      queryClient.setQueryData(contactKeys.detail(contactId), contact);
    },
  });
}

export function useRemoveContactTag(contactId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (tagId: string): Promise<void> => {
      const { error } = await api.DELETE("/api/v1/contacts/{contact_id}/tags/{tag_id}", {
        params: { path: { contact_id: contactId, tag_id: tagId } },
      });
      if (error !== undefined) throw error;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: contactKeys.detail(contactId) });
    },
  });
}
