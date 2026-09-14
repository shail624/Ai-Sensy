import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { Breadcrumbs, PageContainer, PageHeader } from "@/components/layout";
import { DefinitionRow, ErrorState, Section, Spinner } from "@/components/ui";
import {
  apiErrorMessage,
  useTemplate,
  useTemplatePreview,
} from "@/features/templates/api";
import {
  analyzeTemplate,
  componentOf,
  mediaHeaderFormat,
  templateButtons,
} from "@/features/templates/components";
import { TemplateActions } from "@/features/templates/TemplateActions";
import {
  CategoryChip,
  LanguageChip,
  QualityChip,
  SendableMarker,
  TemplateStatusChip,
} from "@/features/templates/TemplateBadges";
import { TemplateBubble } from "@/features/templates/TemplateBubble";
import { TemplateVersionHistory } from "@/features/templates/TemplateVersionHistory";
import { VariableInspector } from "@/features/templates/VariableInspector";
import type { Template } from "@/features/templates/types";
import { STATUS_EXPLANATIONS } from "@/features/templates/types";
import { formatAge, formatDateTime } from "@/lib/format";

const TABS = ["overview", "components", "variables", "history"] as const;
type Tab = (typeof TABS)[number];

const TAB_LABELS: Record<Tab, string> = {
  overview: "Overview",
  components: "Components",
  variables: "Variables",
  history: "Version history",
};

/**
 * The template detail surface (Doc 05 B5.1/B5.2) — the rendered message, the component breakdown,
 * the variable inspector, approval information and version history.
 */
export function TemplateDetail({ templateId }: { templateId: string }): JSX.Element {
  const navigate = useNavigate();
  const [tab, setTab] = useState<Tab>("overview");

  const template = useTemplate(templateId);

  if (template.isLoading) {
    return (
      <PageContainer>
        <Spinner label="Loading template…" />
      </PageContainer>
    );
  }

  if (template.isError || !template.data) {
    return (
      <PageContainer>
        <Breadcrumbs items={[{ label: "Templates", to: "/templates" }, { label: "Template" }]} />
        <ErrorState
          message={apiErrorMessage(template.error)}
          onRetry={() => void template.refetch()}
        />
      </PageContainer>
    );
  }

  const data = template.data;

  return (
    <PageContainer>
      <Breadcrumbs items={[{ label: "Templates", to: "/templates" }, { label: data.name }]} />
      <PageHeader
        title={data.name}
        description={`${data.language} · ${data.category}`}
        actions={<TemplateActions template={data} onDeleted={() => navigate("/templates")} />}
      />

      <div className="mb-4 flex flex-wrap items-center gap-2">
        <TemplateStatusChip value={data.status} />
        <SendableMarker sendable={data.is_sendable} />
        <CategoryChip value={data.category} />
        <LanguageChip value={data.language} />
        <QualityChip value={data.quality_score} />
      </div>

      <nav aria-label="Template sections" className="mb-4 flex flex-wrap gap-2">
        {TABS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setTab(key)}
            aria-current={tab === key ? "page" : undefined}
            className={`rounded-md border px-3 py-1 text-sm ${
              tab === key
                ? "border-accent text-accent"
                : "border-border text-text-secondary hover:bg-hover"
            }`}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
      </nav>

      {tab === "overview" ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <TemplatePreviewSection template={data} />
          <ApprovalSection template={data} />
        </div>
      ) : null}

      {tab === "components" ? <ComponentBreakdown template={data} /> : null}

      {tab === "variables" ? (
        <Section title="Variable inspector">
          <VariableInspector
            analysis={analyzeTemplate(data)}
            mediaHeader={mediaHeaderFormat(data) !== null}
          />
        </Section>
      ) : null}

      {tab === "history" ? <TemplateVersionHistory templateId={templateId} /> : null}
    </PageContainer>
  );
}

/**
 * The message as WhatsApp will show it, rendered by the server (FR-TPL-08).
 *
 * The render is a pure projection — nothing stored, nothing sent — and unsupplied variables stay
 * visible as `{{n}}` on purpose: a preview must not invent a value.
 */
function TemplatePreviewSection({ template }: { template: Template }): JSX.Element {
  const preview = useTemplatePreview(template.id);

  return (
    <Section title="Preview">
      {preview.isLoading ? (
        <Spinner label="Rendering…" />
      ) : preview.isError ? (
        <ErrorState
          message={apiErrorMessage(preview.error)}
          onRetry={() => void preview.refetch()}
        />
      ) : (
        <>
          <TemplateBubble
            header={preview.data?.header ?? ""}
            body={preview.data?.body ?? ""}
            footer={preview.data?.footer ?? ""}
            mediaFormat={mediaHeaderFormat(template)}
            buttons={templateButtons(template)}
          />
          <p className="mt-2 text-xs text-text-disabled">
            Variables are shown as written. Each recipient&apos;s values are bound when a campaign
            maps them.
          </p>
        </>
      )}
    </Section>
  );
}

/** Everything Meta has said about this template, and when we last asked. */
function ApprovalSection({ template }: { template: Template }): JSX.Element {
  return (
    <Section title="Approval">
      <p className="mb-3 text-sm text-text-secondary">
        {STATUS_EXPLANATIONS[template.status] ?? "This template's status came from Meta."}
      </p>

      {template.rejection_reason ? (
        <p role="alert" className="mb-3 rounded-md border border-danger px-3 py-2 text-sm text-danger">
          {template.rejection_reason}
        </p>
      ) : null}

      <dl>
        <DefinitionRow label="Status">
          <TemplateStatusChip value={template.status} />
        </DefinitionRow>
        <DefinitionRow label="Can be sent">
          <SendableMarker sendable={template.is_sendable} />
        </DefinitionRow>
        <DefinitionRow label="Quality rating">
          <QualityChip value={template.quality_score} />
        </DefinitionRow>
        <DefinitionRow label="Last synced">
          {template.last_synced_at ? (
            <>
              {formatDateTime(template.last_synced_at)}{" "}
              <span className="text-text-disabled">({formatAge(template.last_synced_at)})</span>
            </>
          ) : (
            "Never synced from Meta"
          )}
        </DefinitionRow>
        <DefinitionRow label="Created">{formatDateTime(template.created_at)}</DefinitionRow>
        <DefinitionRow label="Last updated">{formatDateTime(template.updated_at)}</DefinitionRow>
      </dl>

      {template.is_sendable ? (
        <p className="mt-3 text-xs text-text-disabled">
          <Link to="/campaigns/new" className="text-accent hover:underline">
            Use it in a campaign
          </Link>{" "}
          to broadcast this template.
        </p>
      ) : null}
    </Section>
  );
}

/** The definition, component by component, with the limits each one is measured against. */
function ComponentBreakdown({ template }: { template: Template }): JSX.Element {
  const header = componentOf(template.components, "header");
  const body = componentOf(template.components, "body");
  const footer = componentOf(template.components, "footer");
  const buttons = templateButtons(template);
  const media = mediaHeaderFormat(template);

  const headerText = typeof header?.text === "string" ? header.text : "";
  const bodyText = typeof body?.text === "string" ? body.text : "";
  const footerText = typeof footer?.text === "string" ? footer.text : "";

  return (
    <div className="space-y-4">
      <Section title="Header">
        {!header ? (
          <p className="text-sm text-text-disabled">No header.</p>
        ) : media ? (
          <p className="text-sm text-text-primary">
            {media} header — the file is supplied per send, not stored on the template.
          </p>
        ) : (
          <p className="whitespace-pre-wrap break-words text-sm text-text-primary">{headerText}</p>
        )}
      </Section>

      <Section title="Body">
        <p className="whitespace-pre-wrap break-words text-sm text-text-primary">{bodyText}</p>
        <p className="mt-2 text-xs text-text-disabled">{bodyText.length} characters</p>
      </Section>

      <Section title="Footer">
        {footerText ? (
          <p className="text-sm text-text-primary">{footerText}</p>
        ) : (
          <p className="text-sm text-text-disabled">No footer.</p>
        )}
      </Section>

      <Section title="Buttons">
        {buttons.length === 0 ? (
          <p className="text-sm text-text-disabled">No buttons.</p>
        ) : (
          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
                <tr>
                  <th scope="col" className="px-3 py-2">Label</th>
                  <th scope="col" className="px-3 py-2">Type</th>
                  <th scope="col" className="px-3 py-2">Target</th>
                </tr>
              </thead>
              <tbody>
                {buttons.map((button, index) => (
                  <tr key={index} className="border-b border-border last:border-0">
                    <td className="px-3 py-2 text-text-primary">{button.text}</td>
                    <td className="px-3 py-2 text-text-secondary">{button.type}</td>
                    <td className="px-3 py-2 font-mono text-xs text-text-secondary">
                      {button.url || button.phone_number || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>
    </div>
  );
}
