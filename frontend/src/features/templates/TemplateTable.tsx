import { Star } from "lucide-react";
import { Link } from "react-router-dom";

import { analyzeTemplate, mediaHeaderFormat } from "@/features/templates/components";
import {
  CategoryChip,
  LanguageChip,
  QualityChip,
  TemplateStatusChip,
} from "@/features/templates/TemplateBadges";
import { TemplateActions } from "@/features/templates/TemplateActions";
import type { Template } from "@/features/templates/types";
import { formatDate } from "@/lib/format";

interface Props {
  templates: Template[];
  favoritePaths?: string[];
  onToggleFavorite?: (path: string) => void;
}

/**
 * The template registry table (Doc 05 B5.1). Rows compose the same badge and action components the
 * detail page uses, so a template reads and behaves identically on both surfaces.
 *
 * Secondary columns drop away below `md` rather than being squeezed: name, approval status and
 * actions are what the list is for, and the rest is one tap away on the detail page.
 */
export function TemplateTable({ templates, favoritePaths = [], onToggleFavorite = () => undefined }: Props): JSX.Element {
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-left text-sm">
        <thead className="border-b border-border bg-surface-2 text-xs text-text-secondary">
          <tr>
            <th scope="col" className="px-3 py-2">Template</th>
            <th scope="col" className="px-3 py-2">Status</th>
            <th scope="col" className="hidden px-3 py-2 lg:table-cell">Category</th>
            <th scope="col" className="hidden px-3 py-2 md:table-cell">Language</th>
            <th scope="col" className="hidden px-3 py-2 lg:table-cell">Variables</th>
            <th scope="col" className="hidden px-3 py-2 xl:table-cell">Quality</th>
            <th scope="col" className="hidden px-3 py-2 xl:table-cell">Created</th>
            <th scope="col" className="px-3 py-2 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          {templates.map((template) => {
            const media = mediaHeaderFormat(template);
            const path = `/templates/${template.id}`;
            const favorite = favoritePaths.includes(path);
            return (
              <tr key={template.id} className="border-b border-border last:border-0 hover:bg-hover">
                <td className="px-3 py-2">
                  <div className="flex items-center gap-2">
                    <Link
                      to={path}
                      className="font-mono font-medium text-text-primary hover:text-accent focus-visible:rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus"
                    >
                      {template.name}
                    </Link>
                    <button
                      type="button"
                      aria-label={favorite ? `Remove ${template.name} from favorites` : `Add ${template.name} to favorites`}
                      aria-pressed={favorite}
                      onClick={() => onToggleFavorite(path)}
                      className={`rounded-md p-1 hover:bg-hover ${favorite ? "text-warning" : "text-text-disabled"}`}
                    >
                      <Star aria-hidden className={`h-3.5 w-3.5 ${favorite ? "fill-current" : ""}`} />
                    </button>
                  </div>
                  <div className="mt-1 flex flex-wrap gap-1 lg:hidden">
                    <CategoryChip value={template.category} />
                    <LanguageChip value={template.language} />
                  </div>
                  {media ? (
                    <p className="mt-1 text-xs text-text-disabled">{media} header</p>
                  ) : null}
                </td>
                <td className="px-3 py-2">
                  <TemplateStatusChip value={template.status} />
                  {template.status === "rejected" && template.rejection_reason ? (
                    <p className="mt-1 max-w-[16rem] truncate text-xs text-danger" title={template.rejection_reason}>
                      {template.rejection_reason}
                    </p>
                  ) : null}
                </td>
                <td className="hidden px-3 py-2 lg:table-cell">
                  <CategoryChip value={template.category} />
                </td>
                <td className="hidden px-3 py-2 md:table-cell">
                  <LanguageChip value={template.language} />
                </td>
                <td className="hidden px-3 py-2 text-text-secondary lg:table-cell">
                  {analyzeTemplate(template).total}
                </td>
                <td className="hidden px-3 py-2 xl:table-cell">
                  <QualityChip value={template.quality_score} />
                </td>
                <td className="hidden px-3 py-2 text-text-secondary xl:table-cell">
                  {formatDate(template.created_at)}
                </td>
                <td className="px-3 py-2">
                  <TemplateActions template={template} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
