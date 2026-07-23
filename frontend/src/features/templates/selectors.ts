import type { Template, TemplateListQuery, TemplateSort } from "@/features/templates/types";

/** Rows per page for the client-side list (see `useTemplates` for why paging lives here). */
export const PAGE_SIZE = 25;

function byName(a: Template, b: Template): number {
  return a.name.localeCompare(b.name);
}

function byCreated(a: Template, b: Template): number {
  return Date.parse(a.created_at) - Date.parse(b.created_at);
}

const COMPARATORS: Record<TemplateSort, (a: Template, b: Template) => number> = {
  "-created_at": (a, b) => byCreated(b, a),
  created_at: byCreated,
  name: byName,
  "-name": (a, b) => byName(b, a),
  "-updated_at": (a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at),
};

/**
 * Case-insensitive match on the template name — the same field the server's `q` filters on.
 *
 * Template names are lower-snake by Meta's rules, so an operator searching "order update" should
 * still find `order_update`: separators are normalised on both sides before comparing.
 */
export function matchesSearch(template: Template, q: string): boolean {
  const needle = q.trim().toLowerCase().replace(/[\s_-]+/g, "");
  if (!needle) return true;
  return template.name.toLowerCase().replace(/[\s_-]+/g, "").includes(needle);
}

export function filterTemplates(templates: Template[], query: TemplateListQuery): Template[] {
  return templates.filter(
    (template) =>
      matchesSearch(template, query.q) &&
      (query.status === "" || template.status === query.status) &&
      (query.category === "" || template.category === query.category) &&
      (query.language === "" || template.language === query.language),
  );
}

export function sortTemplates(templates: Template[], sort: TemplateSort): Template[] {
  return [...templates].sort(COMPARATORS[sort]);
}

/** Every language present in the registry, so the filter offers only what exists. */
export function availableLanguages(templates: Template[]): string[] {
  return [...new Set(templates.map((template) => template.language))].sort();
}

export interface TemplatePage {
  rows: Template[];
  total: number;
  totalPages: number;
  /** Clamped: a filter change that shortens the list must not strand the user on a dead page. */
  page: number;
}

/** Filter → sort → slice, in that order, so the page numbers describe the filtered set. */
export function selectTemplatePage(
  templates: Template[],
  query: TemplateListQuery,
): TemplatePage {
  const matched = sortTemplates(filterTemplates(templates, query), query.sort);
  const totalPages = Math.max(1, Math.ceil(matched.length / PAGE_SIZE));
  const page = Math.min(Math.max(1, query.page), totalPages);
  const start = (page - 1) * PAGE_SIZE;
  return {
    rows: matched.slice(start, start + PAGE_SIZE),
    total: matched.length,
    totalPages,
    page,
  };
}

export interface RegistryCounts {
  total: number;
  approved: number;
  pending: number;
  rejected: number;
  /** Templates that could be broadcast right now — the one question a campaign author asks. */
  sendable: number;
}

/** Headline counts for the list header, so the registry's health reads at a glance. */
export function registryCounts(templates: Template[]): RegistryCounts {
  return {
    total: templates.length,
    approved: templates.filter((template) => template.status === "approved").length,
    pending: templates.filter((template) => template.status === "pending").length,
    rejected: templates.filter((template) => template.status === "rejected").length,
    sendable: templates.filter((template) => template.is_sendable).length,
  };
}
