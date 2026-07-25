import { ArrowRight, FolderLock } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button, EmptyState, Section } from "@/components/ui";
import { useHasPermission } from "@/lib/auth";

/** Media is not contact-linked in the frozen contract, so this section routes to the one document library. */
export function DocumentsSection(): JSX.Element {
  const navigate = useNavigate();
  const canRead = useHasPermission("media:read");
  return <Section title="Documents" description="Secure files stay in the governed media library." icon={<FolderLock aria-hidden className="h-4 w-4" />}><EmptyState compact title="No contact-linked documents" description="The current schema does not associate media assets with a contact. No files are guessed or duplicated here." action={canRead ? <Button variant="secondary" onClick={() => navigate("/media?type=document")} rightIcon={<ArrowRight className="h-4 w-4" />}>Open document library</Button> : undefined} /></Section>;
}
