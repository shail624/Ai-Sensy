import type { components } from "@/lib/api/schema";

// Aliased from the generated OpenAPI schema — never hand-written.
export type Contact = components["schemas"]["ContactResponse"];
export type ContactsPage = components["schemas"]["ContactsPage"];
export type ContactSearchRequest = components["schemas"]["ContactSearchRequest"];
export type SegmentRule = components["schemas"]["SegmentRuleModel"];
export type Tag = components["schemas"]["TagResponse"];
export type AttributeDefinition = components["schemas"]["AttributeDefinitionResponse"];
export type JobAccepted = components["schemas"]["JobAcceptedResponse"];
export type BulkProgress = components["schemas"]["BulkProgressResponse"];
export type ExportProgress = components["schemas"]["ExportProgressResponse"];
export type ImportInspection = components["schemas"]["ImportInspectResponse"];
export type ImportProgress = components["schemas"]["ImportProgressResponse"];

/** The bulk edits the API accepts (`BULK_ACTIONS`, Doc 04 §30). */
export type BulkAction = "add_tags" | "remove_tags" | "set_attributes";
