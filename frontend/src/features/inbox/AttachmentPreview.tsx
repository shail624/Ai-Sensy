import { FileText, Music, Video, X } from "lucide-react";
import { useEffect, useState } from "react";

import type { AttachmentKind } from "@/features/inbox/api";

/** What WhatsApp accepts, per kind — checked before uploading so the agent hears "no" at once. */
const LIMITS: Record<AttachmentKind, { mimes: string[]; maxMb: number; label: string }> = {
  image: { mimes: ["image/jpeg", "image/png"], maxMb: 5, label: "JPG or PNG photos up to 5 MB" },
  video: { mimes: ["video/mp4", "video/3gpp"], maxMb: 16, label: "MP4 or 3GP videos up to 16 MB" },
  audio: {
    mimes: ["audio/aac", "audio/mp4", "audio/mpeg", "audio/amr", "audio/ogg"],
    maxMb: 16,
    label: "MP3, AAC, M4A, AMR or OGG audio up to 16 MB",
  },
  document: {
    mimes: [
      "application/pdf",
      "application/msword",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      "application/vnd.ms-powerpoint",
      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
      "text/plain",
      "text/csv",
    ],
    maxMb: 100,
    label: "PDF, Word, Excel, PowerPoint, TXT or CSV up to 100 MB",
  },
};

/** The `accept` list for each attach-menu choice. */
export const ACCEPT: Record<"media" | "document" | "audio", string> = {
  media: [...LIMITS.image.mimes, ...LIMITS.video.mimes].join(","),
  document: LIMITS.document.mimes.join(","),
  audio: LIMITS.audio.mimes.join(","),
};

/** Which kind a chosen file is, or an error message the agent can act on. */
export function classifyFile(file: File): { kind: AttachmentKind } | { error: string } {
  const type = file.type.split(";")[0]!.trim().toLowerCase();
  const kind = (Object.keys(LIMITS) as AttachmentKind[]).find((key) => LIMITS[key].mimes.includes(type));
  if (!kind) {
    return { error: `This file type (${type || "unknown"}) cannot be sent on WhatsApp. Try a photo, MP4 video, MP3 audio or a PDF/Office document.` };
  }
  const limit = LIMITS[kind];
  if (file.size > limit.maxMb * 1024 * 1024) {
    return { error: `This file is too big. WhatsApp allows ${limit.label}.` };
  }
  return { kind };
}

function sizeLabel(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface Props {
  file: File;
  kind: AttachmentKind;
  onRemove: () => void;
}

/** The chosen file above the message box: a thumbnail for photos, an icon and size otherwise. */
export function AttachmentPreview({ file, kind, onRemove }: Props): JSX.Element {
  const [thumb, setThumb] = useState<string | null>(null);
  useEffect(() => {
    if (kind !== "image" || typeof URL.createObjectURL !== "function") return;
    const url = URL.createObjectURL(file);
    setThumb(url);
    return () => URL.revokeObjectURL(url);
  }, [file, kind]);

  const Icon = kind === "video" ? Video : kind === "audio" ? Music : FileText;
  return (
    <div className="mb-2 flex items-center gap-3 rounded-lg border border-border bg-surface p-2">
      {thumb ? (
        <img src={thumb} alt="" className="h-14 w-14 shrink-0 rounded-md object-cover" />
      ) : (
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-md bg-[#ebf5f3] text-[var(--color-nav-bg)] dark:bg-accent-soft dark:text-accent">
          <Icon aria-hidden className="h-7 w-7" />
        </span>
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-text-primary">{file.name}</p>
        <p className="text-xs text-text-secondary">{sizeLabel(file.size)}</p>
      </div>
      <button type="button" aria-label="Remove attachment" onClick={onRemove} className="flex h-8 w-8 items-center justify-center rounded-full text-text-secondary hover:bg-hover">
        <X aria-hidden className="h-4 w-4" />
      </button>
    </div>
  );
}
