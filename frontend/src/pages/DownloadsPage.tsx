import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DownloadCenter } from "@/features/downloads";

export function DownloadsPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Download Center" }]} />
      <PageHeader
        eyebrow="Generated files"
        title="Download Center"
        description="Track contact exports, analytics reports and chat transcripts, then download them securely when ready."
      />
      <DownloadCenter />
    </PageContainer>
  );
}
