import { Check, Copy, Download, ExternalLink, QrCode } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Modal, Spinner } from "@/components/ui";
import type { PhoneNumber } from "@/features/channels/types";
import { useCopiedFlag } from "@/lib/useCopiedFlag";

const FIELD_CLASS =
  "min-h-11 w-full rounded-lg border border-border bg-surface px-3 py-2 text-sm text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft";
const SECONDARY_ACTION =
  "inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-border px-3 text-sm font-semibold text-text-primary hover:bg-hover disabled:opacity-50";

/** Build Meta's public click-to-chat URL without sending the number or message to another service. */
export function buildWhatsAppChatLink(displayNumber: string, message: string): string | null {
  const digits = displayNumber.replace(/\D/g, "").replace(/^00/, "");
  if (digits.length < 7 || digits.length > 15) return null;

  const url = new URL(`https://wa.me/${digits}`);
  const text = message.trim();
  if (text) url.searchParams.set("text", text);
  return url.toString();
}

interface Props {
  number: PhoneNumber;
  onClose: () => void;
}

/**
 * A private, client-side acquisition utility. The QR image is generated locally from the public
 * click-to-chat URL; no tracking record, external QR service or new backend contract is implied.
 */
export function WhatsAppChatLinkDialog({ number, onClose }: Props): JSX.Element {
  const [message, setMessage] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState<string | null>(null);
  const [qrError, setQrError] = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [copied, markCopied, resetCopied] = useCopiedFlag();
  const link = useMemo(
    () => buildWhatsAppChatLink(number.display_number, message),
    [message, number.display_number],
  );

  useEffect(() => {
    let current = true;
    setQrDataUrl(null);
    setQrError(null);
    if (!link) return () => undefined;

    void import("qrcode")
      .then(({ toDataURL }) =>
        toDataURL(link, {
          errorCorrectionLevel: "M",
          margin: 2,
          width: 320,
          color: { dark: "#073f42", light: "#ffffff" },
        }),
      )
      .then((value) => {
        if (current) setQrDataUrl(value);
      })
      .catch(() => {
        if (current) setQrError("The QR code could not be generated. The chat link is still ready.");
      });

    return () => {
      current = false;
    };
  }, [link]);

  async function copyLink(): Promise<void> {
    resetCopied();
    setCopyError(null);
    if (!link || !navigator.clipboard) {
      setCopyError("Copy is unavailable in this browser. Select the link and copy it manually.");
      return;
    }
    try {
      await navigator.clipboard.writeText(link);
      markCopied();
    } catch {
      setCopyError("Copy was blocked by the browser. Select the link and copy it manually.");
    }
  }

  return (
    <Modal title={`Chat link for ${number.display_number}`} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-xl bg-accent-soft p-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-surface text-accent">
            <QrCode aria-hidden className="h-4 w-4" />
          </span>
          <div>
            <p className="text-sm font-semibold text-text-primary">Start a WhatsApp conversation</p>
            <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">
              Share the link or QR anywhere. A customer opens WhatsApp with your optional message
              ready to send.
            </p>
          </div>
        </div>

        <div>
          <label htmlFor="chat-link-message" className="mb-1.5 block text-sm font-semibold text-text-primary">
            Prefilled message <span className="font-normal text-text-disabled">(optional)</span>
          </label>
          <textarea
            id="chat-link-message"
            rows={3}
            maxLength={512}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Hi, I would like to know more."
            className={FIELD_CLASS}
          />
          <p className="mt-1 text-right text-xs text-text-disabled">{message.length}/512</p>
        </div>

        <div>
          <label htmlFor="chat-link-url" className="mb-1.5 block text-sm font-semibold text-text-primary">
            Shareable link
          </label>
          <input
            id="chat-link-url"
            readOnly
            value={link ?? "This phone number cannot form a public WhatsApp link."}
            className={`${FIELD_CLASS} font-mono text-xs`}
            onFocus={(event) => event.currentTarget.select()}
          />
          {copyError ? <p className="mt-1 text-xs text-danger">{copyError}</p> : null}
        </div>

        <div className="flex flex-wrap gap-2">
          <button type="button" disabled={!link} onClick={() => void copyLink()} className={SECONDARY_ACTION}>
            {copied ? <Check aria-hidden className="h-4 w-4" /> : <Copy aria-hidden className="h-4 w-4" />}
            {copied ? "Copied" : "Copy link"}
          </button>
          {link ? (
            <a href={link} target="_blank" rel="noreferrer" className={SECONDARY_ACTION}>
              <ExternalLink aria-hidden className="h-4 w-4" />
              Test link
            </a>
          ) : null}
          {qrDataUrl ? (
            <a href={qrDataUrl} download="whatsapp-chat-qr.png" className={SECONDARY_ACTION}>
              <Download aria-hidden className="h-4 w-4" />
              Download QR
            </a>
          ) : null}
        </div>

        <div className="flex min-h-52 items-center justify-center rounded-xl border border-border bg-white p-3">
          {!link ? (
            <p className="max-w-xs text-center text-sm text-danger">
              This number needs a valid international format before a QR can be generated.
            </p>
          ) : qrError ? (
            <p className="max-w-xs text-center text-sm text-danger">{qrError}</p>
          ) : qrDataUrl ? (
            <img
              src={qrDataUrl}
              alt={`QR code opening a WhatsApp chat with ${number.display_number}`}
              className="h-48 w-48"
            />
          ) : (
            <Spinner label="Generating QR…" />
          )}
        </div>

        <p className="text-xs leading-relaxed text-text-disabled">
          Generated in this browser. The platform does not upload the message, shorten the link, or
          track scans and clicks.
        </p>
      </div>
    </Modal>
  );
}
