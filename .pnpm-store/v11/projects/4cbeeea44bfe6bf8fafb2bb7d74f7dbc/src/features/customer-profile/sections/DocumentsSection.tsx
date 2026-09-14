import { DocumentWorkspace } from "@/features/documents";

/** Customer 360 projection of the governed document aggregate. */
export function DocumentsSection({ contactId }: { contactId: string }): JSX.Element {
  return <DocumentWorkspace contactId={contactId} compact />;
}
