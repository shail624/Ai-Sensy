import { FileCheck2, History, ShieldCheck } from "lucide-react";

import { Badge, Card } from "@/components/ui";
import { MediaList } from "@/features/media/MediaList";

/** Real upload/preview library with honest boundaries for unimplemented document-domain metadata. */
export function DocumentCenter(): JSX.Element {
  return <div className="space-y-5">
    <div className="grid gap-3 md:grid-cols-3">
      <DocumentCapability icon={ShieldCheck} title="Governed storage" text="Upload, validation, signed preview/download, deduplication, and access control use the existing media service." status="Connected" />
      <DocumentCapability icon={FileCheck2} title="Verification" text="Document approval and expiry require contact linkage and reviewer-state contracts; no status is inferred from filenames." status="Contract gated" />
      <DocumentCapability icon={History} title="Version history" text="The media contract is immutable per asset. Document version lineage requires an additive domain record." status="Contract gated" />
    </div>
    <Card className="p-5" padding={false}><div className="mb-4"><h2 className="text-base font-semibold text-text-primary">Document library</h2><p className="mt-1 text-sm text-text-secondary">Filter to Documents to focus this workspace. Upload and preview are production-backed.</p></div><MediaList /></Card>
  </div>;
}

function DocumentCapability({ icon: Icon, title, text, status }: { icon: typeof ShieldCheck; title: string; text: string; status: string }): JSX.Element {
  return <Card className="p-4" padding={false}><div className="flex items-start justify-between gap-3"><Icon aria-hidden className="h-5 w-5 text-accent" /><Badge tone={status === "Connected" ? "success" : "neutral"}>{status}</Badge></div><h2 className="mt-3 text-sm font-semibold text-text-primary">{title}</h2><p className="mt-1 text-xs leading-relaxed text-text-secondary">{text}</p></Card>;
}
