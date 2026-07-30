import {
  AlertTriangle,
  ArrowUpRight,
  Check,
  Gauge,
  MessageSquareText,
  Phone,
  ShieldCheck,
} from "lucide-react";
import { Link } from "react-router-dom";

import { Badge, Button, Card, CardHeader, ErrorState, Skeleton } from "@/components/ui";
import { apiErrorMessage, useNumbers, useWabas } from "@/features/channels/api";
import type { PhoneNumber, Waba } from "@/features/channels/types";
import {
  isNumberHealthy,
  NUMBER_STATUS_CONNECTED,
  tokenState,
  WABA_STATUS_LABELS,
} from "@/features/channels/types";

export interface WhatsAppOverviewSummary {
  account: Waba | null;
  number: PhoneNumber | null;
  accountReady: boolean;
  numberReady: boolean;
  channelReady: boolean;
  qualityLabel: string;
  completedSteps: number;
}

/** Pick the channel an operator should see first without inventing Meta state. */
export function buildWhatsAppOverview(
  accounts: Waba[],
  numbers: PhoneNumber[],
): WhatsAppOverviewSummary {
  const account = accounts.find((row) => row.status === "active") ?? accounts[0] ?? null;
  const accountNumbers = account
    ? numbers.filter((row) => row.waba_id === account.id)
    : numbers;
  const number =
    accountNumbers.find((row) => row.is_default) ??
    accountNumbers.find((row) => row.status === NUMBER_STATUS_CONNECTED) ??
    accountNumbers[0] ??
    null;
  const accountReady = Boolean(account?.status === "active" && tokenState(account) === "ok");
  const numberReady = number?.status === NUMBER_STATUS_CONNECTED;
  const channelReady = Boolean(accountReady && number && isNumberHealthy(number));
  const qualityLabel =
    number?.quality_rating === "GREEN"
      ? "High"
      : number?.quality_rating === "YELLOW"
        ? "Watch"
        : number?.quality_rating === "RED"
          ? "Low"
          : "Not rated";

  return {
    account,
    number,
    accountReady,
    numberReady,
    channelReady,
    qualityLabel,
    completedSteps: Number(accountReady) + Number(numberReady) + Number(channelReady),
  };
}

function qualityTone(value: string | null | undefined): "success" | "warning" | "danger" | "neutral" {
  if (value === "GREEN") return "success";
  if (value === "YELLOW") return "warning";
  if (value === "RED") return "danger";
  return "neutral";
}

function OverviewLoading(): JSX.Element {
  return (
    <section aria-label="Loading WhatsApp overview" className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <Card>
        <Skeleton className="h-5 w-44" />
        <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((item) => <Skeleton key={item} className="h-20 rounded-xl" />)}
        </div>
        <Skeleton className="mt-5 h-36 rounded-xl" />
      </Card>
      <Card>
        <Skeleton className="h-5 w-32" />
        <Skeleton className="mt-5 h-32 rounded-xl" />
      </Card>
    </section>
  );
}

interface StatusItemProps {
  label: string;
  value: string;
  detail: string;
  icon: JSX.Element;
  tone: "success" | "warning" | "danger" | "neutral";
}

function StatusItem({ label, value, detail, icon, tone }: StatusItemProps): JSX.Element {
  return (
    <div className="rounded-xl bg-surface-2 p-3.5">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-medium text-text-secondary">{label}</p>
        <span className="text-text-disabled">{icon}</span>
      </div>
      <div className="mt-2"><Badge tone={tone} dot>{value}</Badge></div>
      <p className="mt-2 truncate text-xs text-text-disabled" title={detail}>{detail}</p>
    </div>
  );
}

interface SetupStepProps {
  label: string;
  description: string;
  path: string;
  done: boolean;
}

function SetupStep({ label, description, path, done }: SetupStepProps): JSX.Element {
  return (
    <li>
      <Link
        to={path}
        className="group flex items-center gap-3 rounded-xl border border-border px-3 py-2.5 transition-colors hover:border-accent hover:bg-accent-soft/50"
      >
        <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${done ? "bg-success-soft text-success" : "bg-surface-2 text-text-disabled"}`}>
          {done ? <Check aria-hidden className="h-4 w-4" /> : <span aria-hidden className="h-2 w-2 rounded-full border border-current" />}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block text-sm font-medium text-text-primary">{label}</span>
          <span className="mt-0.5 block truncate text-xs text-text-secondary">{description}</span>
        </span>
        <ArrowUpRight aria-hidden className="h-4 w-4 text-text-disabled group-hover:text-accent" />
      </Link>
    </li>
  );
}

/**
 * Setup-first channel summary for the home page. Every status is derived from the existing WABA
 * and phone-number contracts; subscription, credit and quota claims stay absent because the server
 * does not own those records.
 */
export function WhatsAppOverview(): JSX.Element {
  const accounts = useWabas();
  const numbers = useNumbers();

  if (accounts.isLoading || numbers.isLoading) return <OverviewLoading />;

  if (accounts.isError || numbers.isError) {
    const error = accounts.error ?? numbers.error;
    return (
      <Card className="mb-5">
        <CardHeader title="WhatsApp overview" description="Connection status could not be loaded" />
        <div className="mt-4">
          <ErrorState
            message={apiErrorMessage(error)}
            onRetry={() => void Promise.all([accounts.refetch(), numbers.refetch()])}
          />
        </div>
      </Card>
    );
  }

  const summary = buildWhatsAppOverview(accounts.data ?? [], numbers.data ?? []);
  const { account, number } = summary;
  const accountLabel = account
    ? WABA_STATUS_LABELS[account.status] ?? account.status
    : "Not connected";
  const statusLabel = summary.channelReady
    ? "Ready"
    : account
      ? "Needs attention"
      : "Not connected";
  const statusTone = summary.channelReady ? "success" : account ? "warning" : "neutral";
  const healthPath = number ? `/channels/numbers/${number.id}` : "/channels/numbers";

  return (
    <section aria-labelledby="whatsapp-overview-title" className="mb-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
      <Card padding={false} className="overflow-hidden">
        <div className="flex flex-wrap items-start justify-between gap-3 p-4 sm:p-5">
          <div>
            <h2 id="whatsapp-overview-title" className="text-base font-semibold text-text-primary">WhatsApp overview</h2>
            <p className="mt-1 text-sm text-text-secondary">Connection health and the next setup step</p>
          </div>
          <Link to="/channels/accounts">
            <Button variant="ghost" size="sm" rightIcon={<ArrowUpRight className="h-4 w-4" />}>Manage</Button>
          </Link>
        </div>

        <div className="grid grid-cols-1 gap-3 border-y border-border bg-surface-subtle p-4 sm:grid-cols-3 sm:p-5">
          <StatusItem
            label="Business API"
            value={statusLabel}
            detail={account?.business_name ?? "Connect a business account"}
            icon={summary.channelReady ? <ShieldCheck className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
            tone={statusTone}
          />
          <StatusItem
            label="Quality rating"
            value={summary.qualityLabel}
            detail={number?.display_number ?? "No phone number"}
            icon={<MessageSquareText className="h-4 w-4" />}
            tone={qualityTone(number?.quality_rating)}
          />
          <StatusItem
            label="Sending limit"
            value={number ? `${number.mps_limit}/sec` : "Unavailable"}
            detail={number?.messaging_tier ?? "Connect a number to view capacity"}
            icon={<Gauge className="h-4 w-4" />}
            tone={number ? "success" : "neutral"}
          />
        </div>

        <div className="p-4 sm:p-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h3 className="text-sm font-semibold text-text-primary">Set up WhatsApp</h3>
              <p className="mt-0.5 text-xs text-text-secondary">Finish the technical essentials before messaging customers.</p>
            </div>
            <Badge tone={summary.channelReady ? "success" : "accent"}>{summary.completedSteps} of 3 ready</Badge>
          </div>
          <ol className="mt-3 grid gap-2 lg:grid-cols-3">
            <SetupStep
              label="Connect business account"
              description={account ? accountLabel : "Add your Meta business account"}
              path="/channels/accounts"
              done={summary.accountReady}
            />
            <SetupStep
              label="Connect phone number"
              description={number?.display_number ?? "Sync a WhatsApp phone number"}
              path="/channels/numbers"
              done={summary.numberReady}
            />
            <SetupStep
              label="Review channel health"
              description={summary.channelReady ? "Channel is ready to send" : "Resolve quality or connection issues"}
              path={healthPath}
              done={summary.channelReady}
            />
          </ol>
        </div>
      </Card>

      <Card>
        <CardHeader title="Business channel" description="Default WhatsApp identity" icon={<Phone aria-hidden className="h-[18px] w-[18px]" />} />
        {account ? (
          <div className="mt-4">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-accent-soft text-sm font-bold text-accent">
              {account.business_name.slice(0, 2).toUpperCase()}
            </div>
            <p className="mt-3 truncate text-base font-semibold text-text-primary">{account.business_name}</p>
            <p className="mt-1 truncate text-sm text-text-secondary">{number?.verified_name ?? number?.display_number ?? "No number connected"}</p>
            {number?.verified_name && number.display_number ? <p className="mt-0.5 text-xs text-text-disabled">{number.display_number}</p> : null}
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone={account.status === "active" ? "success" : "warning"} dot>{accountLabel}</Badge>
              <Badge tone={qualityTone(number?.quality_rating)}>{summary.qualityLabel}</Badge>
            </div>
            <Link to={number ? `/channels/numbers/${number.id}` : "/channels/accounts"} className="mt-5 block">
              <Button variant="secondary" className="w-full">View channel</Button>
            </Link>
          </div>
        ) : (
          <div className="mt-4 rounded-xl bg-surface-2 p-4">
            <p className="text-sm font-medium text-text-primary">No business account connected</p>
            <p className="mt-1 text-xs leading-relaxed text-text-secondary">Connect the account your team will use for conversations and campaigns.</p>
            <Link to="/channels/accounts" className="mt-4 block">
              <Button className="w-full">Connect account</Button>
            </Link>
          </div>
        )}
      </Card>
    </section>
  );
}
