import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ManagePageHeader } from "@/components/layout";
import { ErrorState, Spinner } from "@/components/ui";
import { QuickGuide } from "@/features/settings/QuickGuide";
import { api } from "@/lib/api/client";
import { apiErrorMessage, unwrap } from "@/lib/api/errors";

const TIMEZONE = Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Kolkata";

function useChatActivity(days: number) {
  return useQuery({
    queryKey: ["chat-activity", days, TIMEZONE],
    queryFn: async () =>
      unwrap(await api.GET("/api/v1/analytics/chat-activity", { params: { query: { days, timezone: TIMEZONE } } })),
    refetchInterval: 60_000,
  });
}

function dayLabel(day: string): string {
  const [year = 1970, month = 1, date = 1] = day.split("-").map(Number);
  return new Date(year, month - 1, date).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

function Total({ label, value, colour }: { label: string; value: number; colour: string }): JSX.Element {
  return (
    <div className="min-w-[140px] rounded-[8px] border border-[#f0f0f0] px-4 py-3 dark:border-border">
      <p className="flex items-center gap-1.5 text-xs text-[#6e6e6e] dark:text-text-secondary">
        <span aria-hidden className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: colour }} /> {label}
      </p>
      <p className="mt-1 text-2xl font-semibold text-black dark:text-text-primary">{value.toLocaleString("en-IN")}</p>
    </div>
  );
}

const USER = "#0a474c";
const BUSINESS = "#28c152";
const BOT = "#f5a623";
const CLOSED = "#3b6fd8";
const INTERVENED = "#e0533d";

/** Manage → Analytics, as the reference: chats per day and agent activity per day. */
export function ChatAnalyticsPage(): JSX.Element {
  const [days, setDays] = useState(7);
  const activity = useChatActivity(days);
  const rows = (activity.data?.data ?? []).map((row) => ({ ...row, label: dayLabel(row.date) }));
  const sum = (key: "user_messages" | "business_messages" | "chatbot_messages" | "closed" | "intervened") =>
    rows.reduce((total, row) => total + row[key], 0);

  return (
    <div className="min-h-full bg-[#f9f9f9] dark:bg-canvas">
      <ManagePageHeader
        title="Analytics"
        actions={
          <select
            aria-label="Period"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
            className="h-9 rounded-[8px] bg-[#f0f0f0] px-3 text-sm text-[#4a4a4a] dark:bg-surface-2 dark:text-text-primary"
          >
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        }
      />
      <div className="mx-auto max-w-[1100px] space-y-5 px-4 py-6 sm:px-[45px]">
        <QuickGuide
          eyebrow="Analytics quick guide"
          text="How busy your WhatsApp was each day: messages from customers, from your team, and automatic replies — and how many chats agents closed or took over."
        />

        {activity.isLoading ? (
          <Spinner label="Loading analytics…" />
        ) : activity.isError ? (
          <ErrorState message={apiErrorMessage(activity.error)} onRetry={() => void activity.refetch()} />
        ) : (
          <>
            <section className="rounded-[8px] bg-surface p-5">
              <h2 className="text-base font-semibold text-black dark:text-text-primary">Chats (per day)</h2>
              <div className="mt-3 flex flex-wrap gap-3">
                <Total label="User Messages" value={sum("user_messages")} colour={USER} />
                <Total label="Chatbot Messages" value={sum("chatbot_messages")} colour={BOT} />
                <Total label="Business Messages" value={sum("business_messages")} colour={BUSINESS} />
              </div>
              <div className="mt-5 h-[280px]" aria-label="Chats per day chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={rows}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={40} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="user_messages" name="User Messages" fill={USER} radius={[3, 3, 0, 0]} />
                    <Bar dataKey="business_messages" name="Business Messages" fill={BUSINESS} radius={[3, 3, 0, 0]} />
                    <Bar dataKey="chatbot_messages" name="Chatbot Messages" fill={BOT} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>

            <section className="rounded-[8px] bg-surface p-5">
              <h2 className="text-base font-semibold text-black dark:text-text-primary">Agent Activity (per day)</h2>
              <div className="mt-3 flex flex-wrap gap-3">
                <Total label="Total Closed" value={sum("closed")} colour={CLOSED} />
                <Total label="Total Intervened" value={sum("intervened")} colour={INTERVENED} />
              </div>
              <div className="mt-5 h-[240px]" aria-label="Agent activity per day chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={rows}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#eee" />
                    <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                    <YAxis allowDecimals={false} tick={{ fontSize: 12 }} width={40} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="closed" name="Closed" fill={CLOSED} radius={[3, 3, 0, 0]} />
                    <Bar dataKey="intervened" name="Intervened" fill={INTERVENED} radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
