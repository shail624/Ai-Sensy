import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DocumentWorkspace } from "@/features/documents/DocumentWorkspace";
import {
  DOCUMENT_STATUS_LABELS,
  DOCUMENT_TYPE_LABELS,
  type CustomerDocument,
} from "@/features/documents/types";

const { permissions, get, post } = vi.hoisted(() => ({
  permissions: { value: ["documents:read", "documents:write", "documents:verify"] },
  get: vi.fn(),
  post: vi.fn(),
}));
vi.mock("@/lib/auth", () => ({
  useHasPermission: (code: string) => permissions.value.includes(code),
}));

let currentDocument: CustomerDocument;

vi.mock("@/lib/api/client", () => ({
  api: { GET: get, POST: post, PATCH: vi.fn(), DELETE: vi.fn() },
  authClient: { POST: vi.fn() },
  setSessionExpiredHandler: vi.fn(),
  refreshOnce: vi.fn(),
}));

function fixture(): CustomerDocument {
  return {
    id: "d1",
    contact_id: "c1",
    document_type: "identity",
    title: "Aadhaar card",
    status: "submitted",
    is_expired: false,
    expires_at: "2027-07-29T00:00:00Z",
    verified_at: null,
    verified_by: null,
    verified_by_name: null,
    rejection_reason: null,
    archived_at: null,
    current_version: {
      id: "v1",
      version_no: 1,
      media_asset_id: "m1",
      file_name: "aadhaar.pdf",
      mime_type: "application/pdf",
      byte_size: 4096,
      note: "Collected at onboarding",
      uploaded_by: "u1",
      uploaded_by_name: "Priya Shah",
      created_at: "2026-07-29T10:00:00Z",
    },
    versions: [],
    version_count: 1,
    row_version: 0,
    created_at: "2026-07-29T10:00:00Z",
    updated_at: "2026-07-29T10:00:00Z",
  };
}

function renderWorkspace() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter><DocumentWorkspace contactId="c1" /></MemoryRouter></QueryClientProvider>);
}

beforeEach(() => {
  permissions.value = ["documents:read", "documents:write", "documents:verify"];
  currentDocument = fixture();
  currentDocument.versions = [currentDocument.current_version];
  get.mockReset();
  post.mockReset();
  get.mockImplementation(async (path: string) => {
    if (path.includes("/history")) {
      return {
        data: {
          data: [
            {
              id: 1,
              event_type: "created",
              actor_user_id: "u1",
              actor_name: "Priya Shah",
              from_value: null,
              to_value: { status: "submitted" },
              reason: null,
              created_at: "2026-07-29T10:00:00Z",
            },
          ],
        },
      };
    }
    if (path.includes("/documents")) return { data: { data: [currentDocument], total: 1 } };
    return { error: new Error("unexpected GET") };
  });
  post.mockImplementation(async (path: string) => {
    if (path.includes("/verification")) {
      currentDocument = {
        ...currentDocument,
        status: "verified",
        verified_at: "2026-07-29T11:00:00Z",
        verified_by: "u1",
        verified_by_name: "Priya Shah",
        row_version: 1,
      };
      return { data: currentDocument };
    }
    return { error: new Error("unexpected POST") };
  });
});

describe("governed customer documents", () => {
  it("derives every status and category label from the generated contract vocabulary", () => {
    expect(Object.keys(DOCUMENT_STATUS_LABELS)).toEqual(["submitted", "verified", "rejected", "expired", "archived"]);
    expect(Object.keys(DOCUMENT_TYPE_LABELS)).toEqual(["identity", "address", "income", "business", "consent", "other"]);
  });

  it("renders premium review metrics and safe file metadata", async () => {
    renderWorkspace();
    expect(await screen.findByText("Aadhaar card")).toBeInTheDocument();
    expect(screen.getAllByText("Awaiting review").length).toBeGreaterThan(0);
    expect(screen.getByText("aadhaar.pdf · 4.0 KB")).toBeInTheDocument();
    expect(screen.getByText("Signed previews only")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Add document" })).toBeEnabled();
  });

  it("opens immutable version and decision history", async () => {
    renderWorkspace();
    fireEvent.click(await screen.findByText("Aadhaar card"));
    expect(await screen.findByRole("heading", { name: "Version history" })).toBeInTheDocument();
    expect(screen.getByText("v1 · aadhaar.pdf")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Decision history" })).toBeInTheDocument();
    expect((await screen.findAllByText(/Priya Shah ·/)).length).toBeGreaterThan(0);
  });

  it("sends the concurrency version when a reviewer verifies", async () => {
    renderWorkspace();
    fireEvent.click(await screen.findByText("Aadhaar card"));
    fireEvent.click(await screen.findByRole("button", { name: "Verify" }));

    await waitFor(() => expect(post).toHaveBeenCalled());
    const [, request] = post.mock.calls[0]!;
    expect(request.body).toMatchObject({ decision: "verified", expected_row_version: 0 });
  });

  it("does not fetch or leak metadata without document read permission", () => {
    permissions.value = [];
    renderWorkspace();
    expect(screen.getByText("Document access is restricted")).toBeInTheDocument();
    expect(get).not.toHaveBeenCalled();
  });
});
