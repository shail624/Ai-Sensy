import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DownloadCenter } from "@/features/downloads";

export function DownloadsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Download Center" }]} />
      <PageHeader
        eyebrow="Generated files"
        title="Download Center"
        description="Your exported files. Download them here when they are ready."
      />
      <DownloadCenter />
    </PageContainer>
  );
}
