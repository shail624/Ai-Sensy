import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import type { MediaAsset, MediaContent, MediaList, MediaType } from "@/features/media/types";

// Shared error helper, re-exported for this feature's components (as tasks and campaigns do).
export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const mediaKeys = {
  all: ["media"] as const,
  list: () => ["media", "list"] as const,
  detail: (id: string) => ["media", "detail", id] as const,
  content: (id: string) => ["media", "content", id] as const,
};

/**
 * The media library.
 *
 * `GET /media` declares **no** query parameters in the contract — the endpoint reads `q`,
 * `filter[media_type][eq]` and `limit` straight off `request.query_params`, so none is reachable
 * from the generated client. It therefore answers with its **default page of 50**, newest first,
 * plus the true `total`. Search, filtering, sorting and paging run in the client over that page
 * (`selectors.ts`), and the UI states plainly when `total` exceeds what it holds — rather than
 * implying the whole library is on screen.
 */
export function useMediaList() {
  return useQuery({
    queryKey: mediaKeys.list(),
    queryFn: async (): Promise<MediaList> => unwrap(await api.GET("/api/v1/media")),
    placeholderData: keepPreviousData,
  });
}

export function useMediaAsset(mediaId: string, enabled = true) {
  return useQuery({
    queryKey: mediaKeys.detail(mediaId),
    queryFn: async (): Promise<MediaAsset> =>
      unwrap(
        await api.GET("/api/v1/media/{media_id}", {
          params: { path: { media_id: mediaId } },
        }),
      ),
    enabled: enabled && Boolean(mediaId),
  });
}

/**
 * A signed, expiring URL for the asset's bytes (FR-MED-09).
 *
 * The signature *is* the credential: the download route it points at is the one media route that is
 * not Bearer-authenticated, which is why the URL can be handed straight to an `<img>`, `<video>` or
 * a download link without leaking a token into markup.
 *
 * It expires — `expires_in` says when — so the query re-issues at 80% of that lifetime. A detail
 * page left open therefore keeps a working preview instead of silently turning into a broken image.
 */
export function useMediaContent(mediaId: string, enabled = true) {
  return useQuery({
    queryKey: mediaKeys.content(mediaId),
    queryFn: async (): Promise<MediaContent> =>
      unwrap(
        await api.GET("/api/v1/media/{media_id}/content", {
          params: { path: { media_id: mediaId } },
        }),
      ),
    enabled: enabled && Boolean(mediaId),
    refetchInterval: (query) => {
      const ttl = query.state.data?.expires_in;
      return ttl && ttl > 0 ? Math.max(30_000, ttl * 800) : false;
    },
    refetchIntervalInBackground: false,
  });
}

/** Every media mutation shifts the list and the asset together. */
function useMediaMutation<TVariables, TData>(
  mutationFn: (variables: TVariables) => Promise<TData>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mediaKeys.all });
    },
  });
}

export interface UploadVariables {
  file: File;
  mediaType: MediaType;
}

/**
 * Upload a file (multipart).
 *
 * **Uploads are deduplicated by SHA-256 within the organization** (FR-MED-05): identical bytes
 * return the *existing* asset rather than storing a second blob. The response looks the same
 * either way, so callers compare the returned `sha256`/`id` when that distinction matters —
 * `useReplaceMedia` does exactly that.
 *
 * The generated body type declares `file` as `string`, because that is how OpenAPI represents
 * binary; the value sent is a real `File`. The cast is at this one boundary and the path and
 * response types remain fully generated.
 */
export function useUploadMedia() {
  return useMediaMutation(
    async ({ file, mediaType }: UploadVariables): Promise<MediaAsset> =>
      unwrap(
        await api.POST("/api/v1/media/upload", {
          body: { file: file as unknown as string, media_type: mediaType },
          bodySerializer(body) {
            const form = new FormData();
            form.append("file", body.file as unknown as File);
            form.append("media_type", body.media_type);
            return form;
          },
        }),
      ),
  );
}

/** Refuses an asset that has been used; `usage_count` is the guard and the server answers 409. */
export function useDeleteMedia() {
  return useMediaMutation(async (mediaId: string): Promise<void> => {
    const { error } = await api.DELETE("/api/v1/media/{media_id}", {
      params: { path: { media_id: mediaId } },
    });
    if (error !== undefined) throw error;
  });
}

export interface ReplaceResult {
  asset: MediaAsset;
  /** True when the new bytes were identical, so dedup returned the same asset and nothing moved. */
  deduped: boolean;
  /** True when the old asset was removed; false when it was in use and had to be kept. */
  replaced: boolean;
}

/**
 * Replace an asset's content.
 *
 * There is no replace endpoint — and there should not be one, because a stored asset is
 * content-addressed by its SHA-256, so "the same asset with different bytes" is a contradiction.
 * Replacement is therefore composed from the two endpoints that exist: upload the new file, then
 * delete the old one.
 *
 * Two outcomes are reported rather than hidden. If the new bytes are identical, dedup returns the
 * *same* asset and deleting it would destroy what was just uploaded — so nothing is deleted. If the
 * old asset has been used, the server refuses to delete it (409) and it is kept; the new asset
 * still exists, and the caller is told the old one remains.
 */
export function useReplaceMedia() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      previousId,
      file,
      mediaType,
    }: UploadVariables & { previousId: string }): Promise<ReplaceResult> => {
      const asset = unwrap(
        await api.POST("/api/v1/media/upload", {
          body: { file: file as unknown as string, media_type: mediaType },
          bodySerializer(body) {
            const form = new FormData();
            form.append("file", body.file as unknown as File);
            form.append("media_type", body.media_type);
            return form;
          },
        }),
      );

      if (asset.id === previousId) return { asset, deduped: true, replaced: false };

      const { error } = await api.DELETE("/api/v1/media/{media_id}", {
        params: { path: { media_id: previousId } },
      });
      // A 409 here means the old asset is in use — the replacement succeeded, the cleanup did not.
      return { asset, deduped: false, replaced: error === undefined };
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mediaKeys.all });
    },
  });
}
