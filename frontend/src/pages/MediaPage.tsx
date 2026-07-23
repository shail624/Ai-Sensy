import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { MediaList } from "@/features/media";

/** Route page for the Media Library (Doc 05 B6.1). */
export function MediaPage(): JSX.Element {
  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Dashboard", to: "/" }, { label: "Media" }]} />
      <PageHeader
        title="Media"
        description="Images, video, audio and documents available to templates and messages."
      />
      <MediaList />
    </PageContainer>
  );
}
