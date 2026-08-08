import { useState } from "react";

import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  LogOut,
  QrCode,
  RefreshCw,
  ShieldAlert,
  Smartphone,
  WifiOff,
} from "lucide-react";

import { Badge, type BadgeTone, Button, Card, CardHeader, EmptyState, ErrorState, Skeleton } from "@/components/ui";
import {
  apiErrorMessage,
  useBeginPairing,
  useConnectWhatsApp,
  useHasPermission,
  useLogoutWhatsApp,
  useReconnectWhatsApp,
  useWhatsAppQrImage,
  useWhatsAppQrStatus,
} from "@/features/whatsapp-qr/api";
import { LogoutConfirmDialog } from "@/features/whatsapp-qr/LogoutConfirmDialog";
import type { WhatsAppQrStatus } from "@/features/whatsapp-qr/types";
import { deriveViewState, type WhatsAppQrViewState } from "@/features/whatsapp-qr/viewState";

const OPERATE_PERMISSION = "channels:authenticate";
const READ_PERMISSION = "channels:read";

const STATUS_BADGE: Record<WhatsAppQrViewState, { label: string; tone: BadgeTone }> = {
  "not-configured": { label: "Not available", tone: "neutral" },
  "ready-to-connect": { label: "Not connected", tone: "neutral" },
  "creating-session": { label: "Starting…", tone: "info" },
  "qr-available": { label: "Scan to connect", tone: "info" },
  "qr-expired": { label: "QR expired", tone: "warning" },
  connecting: { label: "Connecting…", tone: "info" },
  connected: { label: "Connected", tone: "success" },
  "reconnect-available": { label: "Disconnected", tone: "warning" },
  "provider-unavailable": { label: "Unavailable", tone: "danger" },
  "reauth-required": { label: "Needs a new scan", tone: "warning" },
};

function Loading(): JSX.Element {
  return (
    <Card>
      <Skeleton className="h-5 w-48" />
      <div className="mt-5 flex flex-col items-center gap-4 py-6">
        <Skeleton className="h-40 w-40 rounded-xl" />
        <Skeleton className="h-4 w-56" />
      </div>
    </Card>
  );
}

function PermissionDenied(): JSX.Element {
  return (
    <Card>
      <EmptyState
        icon={<ShieldAlert aria-hidden className="h-6 w-6" />}
        title="You don't have access to this"
        description="Viewing the WhatsApp connection requires the channels:read permission. Ask an administrator to grant it if you need to manage this connection."
      />
    </Card>
  );
}

interface QrPanelProps {
  expired: boolean;
  onRetry: () => void;
  retryPending: boolean;
  retryError: unknown;
}

function QrPanel({ expired, onRetry, retryPending, retryError }: QrPanelProps): JSX.Element {
  const { url, loading, error } = useWhatsAppQrImage(!expired);

  return (
    <div className="flex flex-col items-center gap-4 py-4 text-center">
      <div className="flex h-48 w-48 items-center justify-center rounded-xl border border-border bg-surface-2 p-3">
        {expired ? (
          <div className="flex flex-col items-center gap-2 text-text-secondary">
            <AlertTriangle aria-hidden className="h-8 w-8 text-warning" />
            <span className="text-xs">Expired</span>
          </div>
        ) : loading && !url ? (
          <Loader2 aria-hidden className="h-8 w-8 animate-spin text-text-disabled" />
        ) : url ? (
          <img
            src={url}
            alt="Scan this QR code with WhatsApp on the phone to connect"
            className="h-full w-full rounded-lg object-contain"
          />
        ) : (
          <QrCode aria-hidden className="h-8 w-8 text-text-disabled" />
        )}
      </div>
      {expired ? (
        <div className="max-w-sm">
          <p className="text-sm font-medium text-text-primary">This QR code has expired</p>
          <p className="mt-1 text-xs text-text-secondary">
            It was not scanned in time. Request a new one to keep going.
          </p>
          {retryError ? (
            <p className="mt-2 text-xs text-danger">{apiErrorMessage(retryError)}</p>
          ) : null}
          <Button
            className="mt-3"
            size="sm"
            leftIcon={<RefreshCw aria-hidden className="h-3.5 w-3.5" />}
            onClick={onRetry}
            loading={retryPending}
          >
            Get a new QR code
          </Button>
        </div>
      ) : error ? (
        <p className="max-w-sm text-xs text-danger">{apiErrorMessage(error)}</p>
      ) : (
        <div className="max-w-sm">
          <p className="text-sm font-medium text-text-primary">Scan with WhatsApp</p>
          <p className="mt-1 text-xs leading-relaxed text-text-secondary">
            On the phone: WhatsApp → Settings → Linked Devices → Link a Device. The code refreshes
            automatically and is never stored — closing this page discards it.
          </p>
        </div>
      )}
    </div>
  );
}

/**
 * The operator-facing WhatsApp Scan/Connect surface (QR-07).
 *
 * Every rendered state is a direct, honest reflection of `WhatsAppQrStatus` — there is no
 * optimistic "probably connected" guess. In particular this component never infers "disconnected"
 * from a mid-transition `provider_status` (STARTING is genuinely ambiguous per QR-02/QR-06), and
 * it never fetches or shows a QR outside of `qr_available`.
 */
export function WhatsAppQrConnect(): JSX.Element {
  const canRead = useHasPermission(READ_PERMISSION);
  const canOperate = useHasPermission(OPERATE_PERMISSION);
  const [logoutOpen, setLogoutOpen] = useState(false);

  const statusQuery = useWhatsAppQrStatus();
  const connect = useConnectWhatsApp();
  const pair = useBeginPairing();
  const reconnect = useReconnectWhatsApp();
  const logout = useLogoutWhatsApp();

  if (!canRead) return <PermissionDenied />;
  if (statusQuery.isLoading) return <Loading />;
  if (statusQuery.isError) {
    return (
      <Card>
        <ErrorState
          message={apiErrorMessage(statusQuery.error)}
          onRetry={() => void statusQuery.refetch()}
        />
      </Card>
    );
  }

  const status = statusQuery.data as WhatsAppQrStatus;
  const view = deriveViewState(status);
  const badge = STATUS_BADGE[view];
  const identityLabel = status.identity_masked ?? status.push_name ?? "this account";

  return (
    <>
      <Card>
        <CardHeader
          title="WhatsApp connection"
          description="Pair a WhatsApp number with QR scan, and keep it connected."
          icon={<Smartphone aria-hidden className="h-[18px] w-[18px]" />}
          action={<Badge tone={badge.tone} dot>{badge.label}</Badge>}
        />

        <div className="mt-5">
          {view === "not-configured" ? (
            <EmptyState
              icon={<WifiOff aria-hidden className="h-6 w-6" />}
              title="WhatsApp QR connection isn't available"
              description="This isn't set up for your organization yet. Contact your administrator if you expect to see it here."
            />
          ) : null}

          {view === "ready-to-connect" ? (
            <EmptyState
              icon={<QrCode aria-hidden className="h-6 w-6" />}
              title="Connect a WhatsApp number"
              description="Start a connection, then scan the QR code that appears with WhatsApp on the phone."
              action={
                canOperate ? (
                  <Button onClick={() => connect.mutate()} loading={connect.isPending}>
                    Connect WhatsApp
                  </Button>
                ) : (
                  <p className="text-xs text-text-secondary">
                    Connecting requires the channels:authenticate permission.
                  </p>
                )
              }
            />
          ) : null}
          {view === "ready-to-connect" && connect.isError ? (
            <p className="mt-3 text-center text-sm text-danger">{apiErrorMessage(connect.error)}</p>
          ) : null}

          {view === "creating-session" ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <Loader2 aria-hidden className="h-8 w-8 animate-spin text-accent" />
              <div>
                <p className="text-sm font-medium text-text-primary">Starting the session…</p>
                <p className="mt-1 text-xs text-text-secondary">
                  This usually takes a few seconds.
                </p>
              </div>
              {status.pairing_state !== "pairing_requested" && canOperate ? (
                <Button size="sm" onClick={() => pair.mutate()} loading={pair.isPending}>
                  Begin pairing
                </Button>
              ) : null}
              {pair.isError ? (
                <p className="text-xs text-danger">{apiErrorMessage(pair.error)}</p>
              ) : null}
            </div>
          ) : null}

          {view === "qr-available" || view === "qr-expired" ? (
            <QrPanel
              expired={view === "qr-expired"}
              onRetry={() => pair.mutate()}
              retryPending={pair.isPending}
              retryError={pair.error}
            />
          ) : null}

          {view === "connecting" ? (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <Loader2 aria-hidden className="h-8 w-8 animate-spin text-accent" />
              <div>
                <p className="text-sm font-medium text-text-primary">Connecting…</p>
                <p className="mt-1 max-w-xs text-xs text-text-secondary">
                  The session is resuming. This can mean a fresh scan is needed, or that a
                  previously paired phone is reconnecting on its own — both look the same at this
                  point, so we wait rather than guess.
                </p>
              </div>
            </div>
          ) : null}

          {view === "connected" ? (
            <div className="flex flex-col items-center gap-3 py-6 text-center">
              <span className="flex h-14 w-14 items-center justify-center rounded-full bg-success-soft text-success">
                <CheckCircle2 aria-hidden className="h-7 w-7" />
              </span>
              <div>
                <p className="text-sm font-semibold text-text-primary">{identityLabel}</p>
                {status.push_name && status.identity_masked ? (
                  <p className="text-xs text-text-secondary">{status.push_name}</p>
                ) : null}
                <p className="mt-1 text-xs text-text-secondary">
                  Connected and ready to message.
                </p>
              </div>
            </div>
          ) : null}

          {view === "reconnect-available" ? (
            <EmptyState
              icon={<RefreshCw aria-hidden className="h-6 w-6" />}
              title="Connection paused"
              description={status.health_detail}
              action={
                canOperate ? (
                  <Button
                    variant="secondary"
                    leftIcon={<RefreshCw aria-hidden className="h-4 w-4" />}
                    onClick={() => reconnect.mutate()}
                    loading={reconnect.isPending}
                  >
                    Reconnect
                  </Button>
                ) : undefined
              }
            />
          ) : null}
          {view === "reconnect-available" && reconnect.isError ? (
            <p className="mt-3 text-center text-sm text-danger">
              {apiErrorMessage(reconnect.error)}
            </p>
          ) : null}

          {view === "provider-unavailable" ? (
            <EmptyState
              icon={<WifiOff aria-hidden className="h-6 w-6" />}
              title="WhatsApp can't be reached right now"
              description={
                status.health_detail ||
                "The connection service didn't respond. This is usually temporary."
              }
              action={
                <Button variant="secondary" onClick={() => void statusQuery.refetch()}>
                  Check again
                </Button>
              }
            />
          ) : null}

          {view === "reauth-required" ? (
            <EmptyState
              icon={<AlertTriangle aria-hidden className="h-6 w-6" />}
              title="A new scan is needed"
              description={status.health_detail || "Scan a fresh QR code to reconnect this number."}
              action={
                canOperate ? (
                  <Button onClick={() => connect.mutate()} loading={connect.isPending}>
                    Start over
                  </Button>
                ) : undefined
              }
            />
          ) : null}
        </div>
      </Card>

      {view === "connected" && canOperate ? (
        <div className="mt-4 flex justify-end">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<LogOut aria-hidden className="h-3.5 w-3.5" />}
            onClick={() => setLogoutOpen(true)}
          >
            Log out
          </Button>
        </div>
      ) : null}

      {logoutOpen ? (
        <LogoutConfirmDialog
          identityLabel={identityLabel}
          pending={logout.isPending}
          error={logout.error}
          onClose={() => {
            if (!logout.isPending) setLogoutOpen(false);
          }}
          onConfirm={() => {
            logout.mutate(undefined, {
              onSuccess: () => setLogoutOpen(false),
            });
          }}
        />
      ) : null}
    </>
  );
}
