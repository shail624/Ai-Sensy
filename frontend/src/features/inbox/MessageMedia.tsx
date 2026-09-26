import { Download, FileText, ImageOff, Loader2, X } from "lucide-react";
import { useState } from "react";

import { useMessageMedia } from "@/features/inbox/api";
import type { MediaContent } from "@/features/inbox/messageContent";

const INLINE_KINDS = new Set(["image", "sticker", "video", "audio"]);

interface Props {
  messageId: string;
  media: MediaContent;
}

/**
 * The attachment itself, WhatsApp-style: photos and stickers as pictures (tap to enlarge), videos
 * and voice notes with a player, documents as a card with a download button.
 */
export function MessageMedia({ messageId, media }: Props): JSX.Element {
  const inline = INLINE_KINDS.has(media.kind);
  const file = useMessageMedia(messageId, true);
  const [enlarged, setEnlarged] = useState(false);
  const name = media.filename ?? (media.kind === "document" ? "Document" : media.kind);

  if (inline && !file.url) {
    return (
      <div className="flex h-32 w-56 max-w-full items-center justify-center gap-2 rounded-[11px] bg-black/5 text-xs opacity-80">
        {file.failed ? (
          <>
            <ImageOff aria-hidden className="h-4 w-4" /> File not available
          </>
        ) : (
          <>
            <Loader2 aria-hidden className="h-4 w-4 animate-spin" /> Loading {media.kind}…
          </>
        )}
      </div>
    );
  }

  if ((media.kind === "image" || media.kind === "sticker") && file.url) {
    return (
      <>
        <button type="button" onClick={() => setEnlarged(true)} aria-label={`Open ${name}`} className="block overflow-hidden rounded-[11px]">
          <img
            src={file.url}
            alt={media.caption ?? name}
            className={media.kind === "sticker" ? "h-32 w-32 object-contain" : "block max-h-72 w-auto max-w-[260px] object-cover"}
          />
        </button>
        {enlarged ? (
          <div role="dialog" aria-label={name} className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4" onClick={() => setEnlarged(false)}>
            <button type="button" aria-label="Close" className="absolute right-4 top-4 flex h-10 w-10 items-center justify-center rounded-full text-white hover:bg-white/10">
              <X aria-hidden className="h-6 w-6" />
            </button>
            <a
              href={file.url}
              download={media.filename ?? "photo"}
              onClick={(event) => event.stopPropagation()}
              className="absolute right-16 top-4 flex h-10 w-10 items-center justify-center rounded-full text-white hover:bg-white/10"
              aria-label="Download"
            >
              <Download aria-hidden className="h-5 w-5" />
            </a>
            <img src={file.url} alt={media.caption ?? name} className="max-h-full max-w-full object-contain" />
          </div>
        ) : null}
      </>
    );
  }

  if (media.kind === "video" && file.url) {
    return <video src={file.url} controls preload="metadata" className="block max-h-72 w-[260px] max-w-full rounded-[11px] bg-black" />;
  }

  if (media.kind === "audio" && file.url) {
    return <audio src={file.url} controls preload="metadata" className="w-[260px] max-w-full" />;
  }

  // Documents (and anything else): a card with the name and a download button.
  return (
    <div className="flex w-[260px] max-w-full items-center gap-3 rounded-md bg-black/5 p-2">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-white/70 text-[#2563eb]">
        <FileText aria-hidden className="h-6 w-6" />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{name}</p>
        <p className="text-[11px] opacity-70">{file.failed ? "File not available" : file.url ? "Ready to download" : "Loading…"}</p>
      </div>
      {file.url ? (
        <a href={file.url} download={media.filename ?? "document"} aria-label={`Download ${name}`} className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-black/10">
          <Download aria-hidden className="h-4 w-4" />
        </a>
      ) : null}
    </div>
  );
}
