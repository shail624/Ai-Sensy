import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { Badge } from "@/components/ui";
import { ScanWorkspace } from "@/features/scan";

export function ScanPage(): JSX.Element {
  return <PageContainer><Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Scan Studio" }]} /><PageHeader eyebrow="Independent number intelligence" title="Scan Studio" description="Check lists of numbers before you message them." meta={<><Badge tone="info" dot>Coming soon</Badge><span>Not connected to a scanning service yet</span></>} /><ScanWorkspace /></PageContainer>;
}
