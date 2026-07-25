import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge } from "@/components/ui";
import { ScanWorkspace } from "@/features/scan";

export function ScanPage(): JSX.Element {
  return <PageContainer><Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Scan Studio" }]} /><PageHeader eyebrow="Independent number intelligence" title="Scan Studio" description="Prepare, monitor, compare, export, segment, and activate verified scan batches through a module isolated from Meta Cloud API." meta={<><Badge tone="info" dot>Phase 3 integration seam</Badge><span>Separate adapter and queue required</span></>} /><ScanWorkspace /></PageContainer>;
}
