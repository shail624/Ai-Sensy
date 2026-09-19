import { useEffect, useRef, useState } from "react";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import { PAIRING_STATE, type WhatsAppQrStatus } from "@/features/whatsapp-qr/types";

export { apiErrorMessage } from "@/lib/api/errors";
export { useHasPermission } from "@/lib/auth";

export const whatsAppQrKeys = {
  status: ["whatsapp-qr", "session"] as const,
};

/** While the connection is mid-transition, poll fast enough to feel live without hammering it. */
const FAST_POLL_MS = 3_000;
/** Once settled (connected, or genuinely not configured), a slow poll is enough to catch drift. */
const SLOW_POLL_MS = 15_000;

/** Statuses worth polling quickly: nothing has settled into a stable, operator-visible outcome. */
function isTransient(status: WhatsAppQrStatus | undefined): boolean {
  if (!status || !status.configured) return false;
  if (status.connected) return false;
  if (status.requires_reauthentication) return false;
  return true;
}

/**
 * Current WhatsApp QR connection status, self-adjusting its poll rate to the state.
 *
 * A live provider check backs every read (Doc: QR-07 service docstring), so polling here is what
 * makes the screen "live" — there is no separate push channel. The rate backs off once the
 * connection reaches a stable outcome so an idle, already-connected screen does not poll at the
 * same rate as one mid-pairing.
 */
export function useWhatsAppQrStatus(enabled = true) {
  return useQuery({
    queryKey: whatsAppQrKeys.status,
    queryFn: async (): Promise<WhatsAppQrStatus> =>
      unwrap(await api.GET("/api/v1/channels/whatsapp-qr/session")),
    refetchInterval: (query) => (isTransient(query.state.data) ? FAST_POLL_MS : SLOW_POLL_MS),
    enabled,
  });
}

export function useConnectWhatsApp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<WhatsAppQrStatus> =>
      unwrap(await api.POST("/api/v1/channels/whatsapp-qr/session/connect")),
    onSuccess: (data) => queryClient.setQueryData(whatsAppQrKeys.status, data),
  });
}

export function useBeginPairing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<WhatsAppQrStatus> =>
      unwrap(await api.POST("/api/v1/channels/whatsapp-qr/session/pair")),
    onSuccess: (data) => queryClient.setQueryData(whatsAppQrKeys.status, data),
  });
}

export function useReconnectWhatsApp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<WhatsAppQrStatus> =>
      unwrap(await api.POST("/api/v1/channels/whatsapp-qr/session/reconnect")),
    onSuccess: (data) => queryClient.setQueryData(whatsAppQrKeys.status, data),
  });
}

export function useLogoutWhatsApp() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<WhatsAppQrStatus> =>
      unwrap(
        await api.POST("/api/v1/channels/whatsapp-qr/session/logout", {
          body: { confirm: true },
        }),
      ),
    onSuccess: (data) => {
      queryClient.setQueryData(whatsAppQrKeys.status, data);
    },
  });
}

/** How long before the pairing TTL to fetch a fresh QR, so the visible code rarely goes stale. */
const QR_REFRESH_MS = 20_000;

/**
 * The transient QR image, held only as an in-memory object URL — never written to disk, never
 * cached by the browser (`Cache-Control: no-store` from the server), and revoked the moment a
 * newer image replaces it or the caller stops asking for one.
 */
export function useWhatsAppQrImage(enabled: boolean) {
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [loading, setLoading] = useState(false);
  const currentUrl = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled) {
      if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
      currentUrl.current = null;
      setUrl(null);
      return;
    }

    let cancelled = false;

    async function fetchQr(): Promise<void> {
      setLoading(true);
      try {
        // The endpoint documents only its 200 (binary image) response, so the generated client
        // types `error` as unreachable; a non-2xx still lands here as a rejected fetch on the
        // underlying image/png parse, which the surrounding try/catch already handles.
        const response = (await api.GET("/api/v1/channels/whatsapp-qr/session/qr", {
          parseAs: "blob",
        })) as { data?: Blob; error?: unknown };
        if (response.error !== undefined) throw response.error;
        if (cancelled) return;
        if (!response.data) throw new Error("The server returned an empty QR image.");
        const blob = response.data;
        const next = URL.createObjectURL(blob);
        if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
        currentUrl.current = next;
        setUrl(next);
        setError(null);
      } catch (err) {
        if (!cancelled) setError(err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void fetchQr();
    const interval = window.setInterval(() => void fetchQr(), QR_REFRESH_MS);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
     
  }, [enabled]);

  useEffect(
    () => () => {
      if (currentUrl.current) URL.revokeObjectURL(currentUrl.current);
    },
    [],
  );

  return { url, loading, error };
}

export function isQrAvailable(status: WhatsAppQrStatus | undefined): boolean {
  return Boolean(status?.qr_available && status.pairing_state === PAIRING_STATE.PAIRING_AVAILABLE);
}
