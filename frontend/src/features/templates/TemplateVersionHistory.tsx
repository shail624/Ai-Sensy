import { EmptyState, ErrorState, Section, Spinner } from "@/components/ui";
import { apiErrorMessage, useTemplateVersions } from "@/features/templates/api";
import { componentOf } from "@/features/templates/components";
import { CategoryChip, TemplateStatusChip } from "@/features/templates/TemplateBadges";
import { formatDateTime } from "@/lib/format";

/**
 * Every definition this template has had (Doc 03 §7.2).
 *
 * A version is recorded on each create and each edit, so the history shows what was submitted and
 * what Meta said about it — which is what an operator needs after a rejection.
 */
export function TemplateVersionHistory({ templateId }: { templateId: string }): JSX.Element {
  const versions = useTemplateVersions(templateId, true);

  if (versions.isLoading) {
    return (
      <Section title="Version history">
        <Spinner label="Loading history…" />
      </Section>
    );
  }

  if (versions.isError) {
    return (
      <Section title="Version history">
        <ErrorState
          message={apiErrorMessage(versions.error)}
          onRetry={() => void versions.refetch()}
        />
      </Section>
    );
  }

  const rows = [...(versions.data ?? [])].sort((a, b) => b.version_no - a.version_no);

  return (
    <Section title="Version history">
      {rows.length === 0 ? (
        <EmptyState
          title="No versions recorded"
          description="A version is written each time the definition is created or edited."
        />
      ) : (
        <ol className="space-y-3">
          {rows.map((version) => {
            const body = componentOf(version.components, "body");
            const text = typeof body?.text === "string" ? body.text : "";
            return (
              <li key={version.version_no} className="rounded-md border border-border p-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm text-text-primary">v{version.version_no}</span>
                  <TemplateStatusChip value={version.status} />
                  <CategoryChip value={version.category} />
                  <span className="text-xs text-text-secondary">
                    {formatDateTime(version.created_at)}
                  </span>
                </div>
                {text ? (
                  <p className="mt-2 whitespace-pre-wrap break-words text-sm text-text-secondary">
                    {text}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ol>
      )}
    </Section>
  );
}
