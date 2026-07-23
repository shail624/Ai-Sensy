import type { ButtonDraft, HeaderFormat } from "@/features/templates/components";
import { BUTTON_TYPE_LABELS, HEADER_FORMAT_LABELS } from "@/features/templates/components";

/** Glyphs stand in for the media a header will carry; the file itself is bound at send time. */
const MEDIA_GLYPH: Record<string, string> = {
  image: "🖼",
  video: "▶",
  document: "📄",
  location: "📍",
};

interface MediaHeaderProps {
  format: HeaderFormat;
}

/**
 * What a media header will look like in the message.
 *
 * A template declares only the *kind* of media its header carries — the actual file is supplied per
 * send, so there is nothing concrete to show here and inventing a thumbnail would misrepresent the
 * template. The placeholder states the kind, which is the whole of what the template specifies.
 */
export function MediaHeaderPreview({ format }: MediaHeaderProps): JSX.Element {
  return (
    <div className="mb-2 flex h-24 flex-col items-center justify-center rounded-md border border-dashed border-border bg-surface-2">
      <span aria-hidden className="text-2xl">
        {MEDIA_GLYPH[format] ?? "📎"}
      </span>
      <span className="mt-1 text-xs text-text-secondary">
        {HEADER_FORMAT_LABELS[format]} header
      </span>
      <span className="text-xs text-text-disabled">Supplied per send</span>
    </div>
  );
}

interface Props {
  header: string;
  body: string;
  footer: string;
  /** A media kind when the header carries a file, `null` for a text header or none at all. */
  mediaFormat: HeaderFormat | null;
  buttons: ButtonDraft[];
}

/**
 * The template as a WhatsApp message.
 *
 * Text arrives already rendered — from the server's preview endpoint on the detail page, or from
 * the draft being typed in the editor. Unsupplied variables stay visible as `{{n}}` because that is
 * what the renderer does on purpose: a preview must not invent a value.
 */
export function TemplateBubble({
  header,
  body,
  footer,
  mediaFormat,
  buttons,
}: Props): JSX.Element {
  return (
    <div className="rounded-lg bg-surface-2 p-3">
      <div className="max-w-sm rounded-lg border border-border bg-surface p-3 shadow-sm">
        {mediaFormat ? <MediaHeaderPreview format={mediaFormat} /> : null}

        {header ? (
          <p className="mb-1 text-sm font-semibold text-text-primary">{header}</p>
        ) : null}

        <p className="whitespace-pre-wrap break-words text-sm text-text-primary">
          {body || <span className="text-text-disabled">No body text yet.</span>}
        </p>

        {footer ? <p className="mt-2 text-xs text-text-disabled">{footer}</p> : null}

        {buttons.length > 0 ? (
          <div className="mt-3 space-y-1 border-t border-border pt-2">
            {buttons.map((button, index) => (
              <div
                key={`${button.type}-${index}`}
                className="rounded-md border border-border px-2 py-1 text-center text-xs text-accent"
              >
                {button.text || BUTTON_TYPE_LABELS[button.type]}
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </div>
  );
}
