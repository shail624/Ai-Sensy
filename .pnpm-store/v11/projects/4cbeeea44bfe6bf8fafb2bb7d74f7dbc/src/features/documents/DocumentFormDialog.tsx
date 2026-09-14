import { ShieldCheck } from "lucide-react";
import { useState } from "react";

import { Badge, Button, Modal } from "@/components/ui";
import { DocumentAssetPicker } from "@/features/documents/DocumentAssetPicker";
import {
  apiErrorMessage,
  useAddDocumentVersion,
  useCreateDocument,
} from "@/features/documents/api";
import {
  DOCUMENT_TYPES,
  DOCUMENT_TYPE_LABELS,
  type CustomerDocument,
  type DocumentType,
} from "@/features/documents/types";
import type { MediaAsset } from "@/features/media/types";

const FIELD =
  "mt-1 h-10 w-full rounded-lg border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-accent focus:ring-2 focus:ring-accent-soft";
const LABEL = "text-xs font-semibold text-text-secondary";

interface Props {
  contactId: string;
  document?: CustomerDocument;
  onClose: () => void;
  onSaved?: (document: CustomerDocument) => void;
}

export function DocumentFormDialog({ contactId, document, onClose, onSaved }: Props): JSX.Element {
  const [title, setTitle] = useState("");
  const [type, setType] = useState<DocumentType>("identity");
  const [expiresAt, setExpiresAt] = useState("");
  const [note, setNote] = useState("");
  const [asset, setAsset] = useState<MediaAsset | null>(null);
  const [attempted, setAttempted] = useState(false);
  const create = useCreateDocument(contactId);
  const version = useAddDocumentVersion(contactId, document?.id ?? "");
  const mutation = document ? version : create;
  const invalid = !asset || (!document && !title.trim());

  function submit(): void {
    setAttempted(true);
    if (invalid || !asset) return;
    if (document) {
      version.mutate(
        {
          media_asset_id: asset.id,
          note: note.trim() || undefined,
          expected_row_version: document.row_version,
        },
        { onSuccess: (saved) => onSaved?.(saved) },
      );
      return;
    }
    create.mutate(
      {
        document_type: type,
        title: title.trim(),
        media_asset_id: asset.id,
        expires_at: expiresAt ? new Date(`${expiresAt}T23:59:59`).toISOString() : undefined,
        note: note.trim() || undefined,
      },
      { onSuccess: (saved) => onSaved?.(saved) },
    );
  }

  return (
    <Modal title={document ? `Add a version to ${document.title}` : "Add customer document"} onClose={onClose} variant="sheet">
      <div className="space-y-4">
        <div className="flex items-start gap-3 rounded-xl border border-success/20 bg-success/5 p-3">
          <ShieldCheck aria-hidden className="mt-0.5 h-4 w-4 shrink-0 text-success" />
          <div>
            <p className="text-xs font-semibold text-text-primary">Governed and traceable</p>
            <p className="mt-0.5 text-xs leading-relaxed text-text-secondary">
              Every file version is immutable, scanned, tenant-isolated, and recorded in customer history.
            </p>
          </div>
          <Badge tone="success">Secure</Badge>
        </div>

        {!document ? (
          <div className="grid gap-3 sm:grid-cols-2">
            <label className={LABEL}>
              Document name
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="e.g. Aadhaar card"
                maxLength={160}
                className={FIELD}
                autoFocus
              />
            </label>
            <label className={LABEL}>
              Category
              <select value={type} onChange={(event) => setType(event.target.value as DocumentType)} className={FIELD}>
                {DOCUMENT_TYPES.map((option) => (
                  <option key={option} value={option}>{DOCUMENT_TYPE_LABELS[option]}</option>
                ))}
              </select>
            </label>
            <label className={LABEL}>
              Expiry date <span className="font-normal text-text-disabled">(optional)</span>
              <input type="date" value={expiresAt} onChange={(event) => setExpiresAt(event.target.value)} className={FIELD} />
            </label>
            <label className={LABEL}>
              Collection note <span className="font-normal text-text-disabled">(optional)</span>
              <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Source or context" maxLength={2000} className={FIELD} />
            </label>
          </div>
        ) : (
          <label className={LABEL}>
            Version note <span className="font-normal text-text-disabled">(optional)</span>
            <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="What changed in this version?" maxLength={2000} className={FIELD} autoFocus />
          </label>
        )}

        <div>
          <p className="mb-2 text-xs font-semibold text-text-secondary">Secure file</p>
          <DocumentAssetPicker value={asset} onChange={setAsset} />
        </div>

        {attempted && invalid ? (
          <p role="alert" className="text-sm text-danger">
            {!asset ? "Select or upload a file to continue." : "Enter a document name."}
          </p>
        ) : null}
        {mutation.isError ? <p role="alert" className="text-sm text-danger">{apiErrorMessage(mutation.error)}</p> : null}

        <div className="sticky bottom-0 -mx-4 flex justify-end gap-2 border-t border-border bg-surface px-4 pt-3">
          <Button variant="secondary" onClick={onClose} disabled={mutation.isPending}>Cancel</Button>
          <Button onClick={submit} loading={mutation.isPending}>
            {document ? "Add version" : "Add document"}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
