import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AlertToggle } from "./AlertToggle";
import { customerTitle, newlyUnread, readAlertPrefs } from "./messageAlerts";
import type { Conversation } from "./types";

const conversation = (id: string, unread: number, name: string | null = "Shailesh Kumar"): Conversation =>
  ({ id, unread_count: unread, contact: { id: `c-${id}`, name, phone: "+919891000010" } }) as Conversation;

describe("newlyUnread", () => {
  it("never rings on the first look, only when a chat's unread count rises", () => {
    expect(newlyUnread(null, [conversation("a", 3)])).toEqual([]);
    const seen = new Map([["a", 1], ["b", 0]]);
    const rows = [conversation("a", 2), conversation("b", 0), conversation("c", 1)];
    expect(newlyUnread(seen, rows).map((row) => row.id)).toEqual(["a", "c"]);
  });

  it("stays quiet when a chat is read", () => {
    expect(newlyUnread(new Map([["a", 4]]), [conversation("a", 0)])).toEqual([]);
  });
});

describe("customerTitle", () => {
  it("shows both the WhatsApp name and the number", () => {
    expect(customerTitle(conversation("a", 1))).toBe("Shailesh Kumar (+919891000010)");
    expect(customerTitle(conversation("a", 1, null))).toBe("+919891000010");
  });
});

describe("AlertToggle", () => {
  beforeEach(() => localStorage.clear());

  it("defaults to sound on and remembers the choice", () => {
    render(<AlertToggle />);
    fireEvent.click(screen.getByRole("button", { name: "New message alerts on" }));
    const sound = screen.getByRole("checkbox", { name: "Play a sound" });
    expect(sound).toBeChecked();
    fireEvent.click(sound);
    expect(readAlertPrefs().sound).toBe(false);
  });

  it("asks the browser before turning desktop notifications on", async () => {
    const requestPermission = vi.fn(() => Promise.resolve("granted" as NotificationPermission));
    vi.stubGlobal("Notification", Object.assign(vi.fn(), { permission: "default", requestPermission }));
    render(<AlertToggle />);
    fireEvent.click(screen.getByRole("button", { name: /New message alerts/ }));
    fireEvent.click(screen.getByRole("checkbox", { name: "Show a desktop notification" }));
    await vi.waitFor(() => expect(readAlertPrefs().desktop).toBe(true));
    expect(requestPermission).toHaveBeenCalledOnce();
    vi.unstubAllGlobals();
  });
});

describe("newReminders", () => {
  it("rings only for reminders that appeared since the last poll", async () => {
    const { newReminders } = await import("./messageAlerts");
    const a = { id: "a", type: "follow_up_due", title: "Reminder: A", body: "call" };
    const b = { id: "b", type: "release_date_due", title: "Release date today: B", body: "" };
    const other = { id: "c", type: "report_ready", title: "Report", body: "" };
    expect(newReminders(null, [a])).toEqual([]);
    expect(newReminders(new Set(["a"]), [a, b, other])).toEqual([b]);
  });
});
