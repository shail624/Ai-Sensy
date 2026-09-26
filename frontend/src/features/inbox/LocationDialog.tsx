import { LocateFixed } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Modal } from "@/components/ui";
import { apiErrorMessage, useSendLocation } from "@/features/inbox/api";

/**
 * Coordinates from what an agent is likely to paste: "28.61, 77.20", or a Google Maps link
 * ("…/@28.61,77.20,15z", "…?q=28.61,77.20", "…!3d28.61!4d77.20"). `null` when none is found.
 */
export function parseCoordinates(text: string): { latitude: number; longitude: number } | null {
  const patterns = [
    /!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)/,
    /@(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)/,
    /[?&](?:q|query|ll|destination)=(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)/,
    /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/,
  ];
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match) {
      const latitude = Number(match[1]);
      const longitude = Number(match[2]);
      if (Math.abs(latitude) <= 90 && Math.abs(longitude) <= 180) return { latitude, longitude };
    }
  }
  return null;
}

const input =
  "mt-2 h-[42px] w-full rounded-[8px] bg-[#f0f0f0] px-[15px] text-sm text-[#4a4a4a] placeholder:text-[#9e9e9e] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus dark:bg-surface-2 dark:text-text-primary";

export function LocationDialog({ conversationId, onClose }: { conversationId: string; onClose: () => void }): JSX.Element {
  const [where, setWhere] = useState("");
  const [name, setName] = useState("");
  const [locating, setLocating] = useState(false);
  const [locateError, setLocateError] = useState<string | null>(null);
  const send = useSendLocation(conversationId);
  const coordinates = parseCoordinates(where);

  function useMyLocation(): void {
    if (!navigator.geolocation) {
      setLocateError("This browser cannot share its location. Paste a Google Maps link instead.");
      return;
    }
    setLocating(true);
    setLocateError(null);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocating(false);
        setWhere(`${position.coords.latitude.toFixed(6)}, ${position.coords.longitude.toFixed(6)}`);
      },
      () => {
        setLocating(false);
        setLocateError("Location permission was denied. Paste a Google Maps link instead.");
      },
      { enableHighAccuracy: true, timeout: 10_000 },
    );
  }

  function submit(event: FormEvent): void {
    event.preventDefault();
    if (!coordinates) return;
    send.mutate({ ...coordinates, name: name.trim() || null }, { onSuccess: onClose });
  }

  return (
    <Modal title="Send a location" onClose={onClose} panelClassName="!max-w-[460px] !rounded-md" contentClassName="!px-6">
      <form onSubmit={submit} className="space-y-4">
        <button
          type="button"
          onClick={useMyLocation}
          disabled={locating}
          className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md border border-[rgba(10,71,76,0.5)] text-sm font-medium text-[var(--color-nav-bg)] hover:bg-[#ebf5f3] disabled:opacity-60 dark:text-accent"
        >
          <LocateFixed aria-hidden className="h-4 w-4" /> {locating ? "Finding you…" : "Use my current location"}
        </button>
        <div>
          <label htmlFor="location-where" className="text-sm font-medium text-text-primary">Google Maps link or coordinates</label>
          <input
            id="location-where"
            value={where}
            onChange={(event) => setWhere(event.target.value)}
            placeholder="https://maps.google.com/… or 28.6139, 77.2090"
            className={input}
          />
          <p className="mt-1.5 text-xs text-[#6e6e6e] dark:text-text-secondary">
            {where && !coordinates
              ? "No location found in this text. In Google Maps, open the place and copy the link from the address bar."
              : coordinates
                ? `Pin: ${coordinates.latitude}, ${coordinates.longitude}`
                : "Open the place in Google Maps and paste the link here."}
          </p>
        </div>
        <div>
          <label htmlFor="location-name" className="text-sm font-medium text-text-primary">Place name (optional)</label>
          <input id="location-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="e.g. Vi Store, Connaught Place" className={input} />
        </div>
        {locateError ? <p role="alert" className="text-xs text-danger">{locateError}</p> : null}
        {send.error ? <p role="alert" className="rounded-md bg-danger-soft px-3 py-2 text-sm text-danger-on-soft">{apiErrorMessage(send.error)}</p> : null}
        <div className="flex justify-end gap-2 border-t border-border pt-3">
          <button type="button" onClick={onClose} className="h-9 rounded-md px-4 text-sm font-medium text-[#4a4a4a] hover:bg-hover dark:text-text-secondary">Cancel</button>
          <button
            type="submit"
            disabled={!coordinates || send.isPending}
            className="inline-flex h-9 items-center rounded-md bg-[var(--color-nav-bg)] px-4 text-sm font-medium text-white transition-colors hover:bg-[#08393d] disabled:opacity-60"
          >
            {send.isPending ? "Sending…" : "Send location"}
          </button>
        </div>
      </form>
    </Modal>
  );
}
