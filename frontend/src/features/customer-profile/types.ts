import type { components } from "@/lib/api/schema";

// Types are aliased straight from the generated OpenAPI schema — never hand-written.
export type Contact = components["schemas"]["ContactResponse"];
export type TagSummary = components["schemas"]["TagSummary"];
export type Tag = components["schemas"]["TagResponse"];
export type ContactEvent = components["schemas"]["ContactEventResponse"];
export type AttributeDefinition = components["schemas"]["AttributeDefinitionResponse"];
export type Note = components["schemas"]["NoteResponse"];
