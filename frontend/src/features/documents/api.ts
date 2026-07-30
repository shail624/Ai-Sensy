import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import type {
  CustomerDocument,
  DocumentCreateRequest,
  DocumentEvent,
  DocumentFilters,
  DocumentVerificationRequest,
  DocumentVersionCreateRequest,
} from "@/features/documents/types";
import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";

export { apiErrorMessage } from "@/lib/api/errors";

export const documentKeys = {
  all: ["documents"] as const,
  list: (contactId: string) => ["documents", "contact", contactId] as const,
  history: (documentId: string) => ["documents", documentId, "history"] as const,
};

export function useContactDocuments(contactId: string, filters: DocumentFilters) {
  return useQuery({
    queryKey: [...documentKeys.list(contactId), filters],
    queryFn: async () =>
      unwrap(
        await api.GET("/api/v1/contacts/{contact_id}/documents", {
          params: {
            path: { contact_id: contactId },
            query: {
              q: filters.q || undefined,
              status: filters.status ? [filters.status] : undefined,
              type: filters.type ? [filters.type] : undefined,
              limit: 200,
            },
          },
        }),
      ),
    enabled: Boolean(contactId),
  });
}

export function useDocumentHistory(documentId: string | null) {
  return useQuery({
    queryKey: documentKeys.history(documentId ?? ""),
    queryFn: async (): Promise<DocumentEvent[]> =>
      unwrap(
        await api.GET("/api/v1/documents/{document_id}/history", {
          params: { path: { document_id: documentId! } },
        }),
      ).data,
    enabled: Boolean(documentId),
  });
}

function useDocumentMutation<TVariables>(
  contactId: string,
  mutationFn: (variables: TVariables) => Promise<CustomerDocument>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: (document) => {
      void queryClient.invalidateQueries({ queryKey: documentKeys.list(contactId) });
      void queryClient.invalidateQueries({ queryKey: documentKeys.history(document.id) });
      void queryClient.invalidateQueries({ queryKey: ["contact", contactId, "timeline"] });
    },
  });
}

export function useCreateDocument(contactId: string) {
  return useDocumentMutation(
    contactId,
    async (body: DocumentCreateRequest): Promise<CustomerDocument> =>
      unwrap(
        await api.POST("/api/v1/contacts/{contact_id}/documents", {
          params: { path: { contact_id: contactId } },
          body,
        }),
      ),
  );
}

export function useAddDocumentVersion(contactId: string, documentId: string) {
  return useDocumentMutation(
    contactId,
    async (body: DocumentVersionCreateRequest): Promise<CustomerDocument> =>
      unwrap(
        await api.POST("/api/v1/documents/{document_id}/versions", {
          params: { path: { document_id: documentId } },
          body,
        }),
      ),
  );
}

export function useVerifyDocument(contactId: string, documentId: string) {
  return useDocumentMutation(
    contactId,
    async (body: DocumentVerificationRequest): Promise<CustomerDocument> =>
      unwrap(
        await api.POST("/api/v1/documents/{document_id}/verification", {
          params: { path: { document_id: documentId } },
          body,
        }),
      ),
  );
}

export function useArchiveDocument(contactId: string, documentId: string) {
  return useDocumentMutation(
    contactId,
    async ({ reason, expectedRowVersion }: { reason?: string; expectedRowVersion: number }) =>
      unwrap(
        await api.POST("/api/v1/documents/{document_id}/archive", {
          params: { path: { document_id: documentId } },
          body: { reason, expected_row_version: expectedRowVersion },
        }),
      ),
  );
}

export function useExpireDocument(contactId: string, documentId: string) {
  return useDocumentMutation(
    contactId,
    async ({ expectedRowVersion }: { expectedRowVersion: number }) =>
      unwrap(
        await api.POST("/api/v1/documents/{document_id}/expire", {
          params: { path: { document_id: documentId } },
          body: { expected_row_version: expectedRowVersion },
        }),
      ),
  );
}

export function useDocumentContent() {
  return useMutation({
    mutationFn: async ({ documentId, versionId }: { documentId: string; versionId: string }) =>
      unwrap(
        await api.GET("/api/v1/documents/{document_id}/versions/{version_id}/content", {
          params: { path: { document_id: documentId, version_id: versionId } },
        }),
      ),
  });
}
