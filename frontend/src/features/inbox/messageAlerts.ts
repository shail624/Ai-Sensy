import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { api } from "@/lib/api/client";
import { unwrap } from "@/lib/api/errors";
import { toListQuery } from "@/features/inbox/api";
import type { Conversation } from "@/features/inbox/types";

const PREFS_KEY = "wa.message-alerts.v1";
const POLL_MS = 10_000;

export interface AlertPrefs {
  sound: boolean;
  desktop: boolean;
}

const DEFAULT_PREFS: AlertPrefs = { sound: true, desktop: false };

export function readAlertPrefs(): AlertPrefs {
  try {
    const raw = localStorage.getItem(PREFS_KEY);
    return raw ? { ...DEFAULT_PREFS, ...(JSON.parse(raw) as Partial<AlertPrefs>) } : DEFAULT_PREFS;
  } catch {
    return DEFAULT_PREFS;
  }
}

function writeAlertPrefs(prefs: AlertPrefs): void {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs));
  } catch {
    // Private mode or blocked storage: the choice simply lasts for this page.
  }
  window.dispatchEvent(new Event(PREFS_KEY));
}

/** The user's alert choices, shared by every component that reads or changes them. */
export function useAlertPrefs(): [AlertPrefs, (next: AlertPrefs) => void] {
  const [prefs, setPrefs] = useState<AlertPrefs>(readAlertPrefs);
  useEffect(() => {
    const sync = (): void => setPrefs(readAlertPrefs());
    window.addEventListener(PREFS_KEY, sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener(PREFS_KEY, sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  const update = useCallback((next: AlertPrefs) => {
    setPrefs(next);
    writeAlertPrefs(next);
  }, []);
  return [prefs, update];
}

let audio: AudioContext | null = null;

/** A short two-note chime generated in the browser (no sound file to load or cache). */
export function playChime(): void {
  try {
    const Ctx = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    audio ??= new Ctx();
    if (audio.state === "suspended") void audio.resume();
    const now = audio.currentTime;
    [880, 1320].forEach((frequency, index) => {
      const oscillator = audio!.createOscillator();
      const gain = audio!.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      const start = now + index * 0.12;
      gain.gain.setValueAtTime(0.0001, start);
      gain.gain.exponentialRampToValueAtTime(0.25, start + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.25);
      oscillator.connect(gain).connect(audio!.destination);
      oscillator.start(start);
      oscillator.stop(start + 0.26);
    });
  } catch {
    // Audio is a nicety; a browser that refuses it must not break the page.
  }
}

/**
 * Compare two polls and return the conversations that gained unread messages. The first poll only
 * records the baseline, so opening the app never rings for messages that were already waiting.
 */
export function newlyUnread(previous: Map<string, number> | null, current: Conversation[]): Conversation[] {
  if (previous === null) return [];
  return current.filter((conversation) => conversation.unread_count > (previous.get(conversation.id) ?? 0));
}

/** "Name (+number)", or whichever of the two is known — agents asked to see both. */
export function customerTitle(conversation: Conversation): string {
  const name = conversation.contact?.name?.trim();
  const phone = conversation.contact?.phone?.trim();
  if (name && phone && name !== phone) return `${name} (${phone})`;
  return name || phone || "New message";
}

/**
 * Sound and desktop alerts for new customer messages, on every screen. Polls the newest chats
 * (the platform has no push channel yet) and alerts when a chat's unread count rises — except the
 * chat already open in a visible tab, which the agent is reading anyway.
 */
export function useNewMessageAlerts(enabled: boolean): void {
  const [prefs] = useAlertPrefs();
  const navigate = useNavigate();
  const location = useLocation();
  const seen = useRef<Map<string, number> | null>(null);
  const active = enabled && (prefs.sound || prefs.desktop);

  const latest = useQuery({
    queryKey: ["message-alerts"],
    queryFn: async (): Promise<Conversation[]> =>
      unwrap(await api.GET("/api/v1/conversations", { params: { query: toListQuery({}, null, 25) } }))
        .data,
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: true,
    enabled: active,
  });

  useEffect(() => {
    if (!active) seen.current = null;
  }, [active]);

  useEffect(() => {
    const rows = latest.data;
    if (!rows) return;
    const fresh = newlyUnread(seen.current, rows);
    seen.current = new Map(rows.map((row) => [row.id, row.unread_count]));

    const openId = new URLSearchParams(location.search).get("conversation");
    const worthAlerting = fresh.filter(
      (row) => !(row.id === openId && document.visibilityState === "visible"),
    );
    if (worthAlerting.length === 0) return;

    if (prefs.sound) playChime();
    if (prefs.desktop && typeof Notification !== "undefined" && Notification.permission === "granted") {
      for (const row of worthAlerting.slice(0, 3)) {
        const notification = new Notification(customerTitle(row), {
          body: row.last_message_preview ?? "New message",
          tag: `conversation-${row.id}`,
        });
        notification.onclick = () => {
          window.focus();
          navigate(`/inbox?conversation=${row.id}`);
          notification.close();
        };
      }
    }
    // Only a new poll result should ring; route or preference changes must not replay it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latest.data]);
}
