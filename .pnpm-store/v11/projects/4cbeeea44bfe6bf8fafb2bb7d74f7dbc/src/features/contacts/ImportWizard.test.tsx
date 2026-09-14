import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ImportWizard } from "@/features/contacts/ImportWizard";

const posts: { path: string; body: Record<string, unknown> }[] = [];
const importProgress = {
  value: {
    id: "i1",
    type: "import",
    status: "running",
    format: "csv",
    dedup_strategy: "skip",
    total_rows: 2,
    processed_rows: 1,
    success_rows: 1,
    error_rows: 0,
    error_report_url: null as string | null,
    created_at: "2026-07-24T00:00:00Z",
    completed_at: null as string | null,
  },
};
const inspection = {
  value: {
    type: "import_inspection",
    headers: ["Phone Number", "Full Name"],
    sample_row: ["+14155550001", "Priya Sharma"],
    sheet_name: "Contacts",
    estimated_rows: 2,
    errors: [] as { field: string; code: string; message: string }[],
  },
};

vi.mock("@/lib/api/client", () => {
  const GET = async (path: string) => {
    if (path === "/api/v1/custom-attributes") return { data: [] };
    if (path === "/api/v1/tags") return { data: [] };
    if (path === "/api/v1/contacts/import/{import_id}") return { data: importProgress.value };
    return { error: new Error(`no stub for ${path}`) };
  };
  const POST = async (path: string, init: { body: Record<string, unknown> }) => {
    posts.push({ path, body: init.body });
    if (path === "/api/v1/media/upload") return { data: { id: "media-1", media_type: "document" } };
    if (path === "/api/v1/contacts/import/inspect") return { data: inspection.value };
    return { data: { job: { id: "i1", type: "import", status: "queued", poll_url: "/x" } } };
  };
  const write = async () => ({ error: new Error("network disabled under test") });
  return {
    api: { GET, POST, PATCH: write, PUT: write, DELETE: write },
    authClient: { POST: write },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

const CSV = "Phone Number,Full Name,Loyalty tier\n+14155550001,Priya Sharma,gold\n+14155550002,Marcus Webb,silver\n";

function csvFile(name = "contacts.csv", content = CSV): File {
  return new File([content], name, { type: "text/csv" });
}

function xlsxFile(): File {
  return new File(["mock workbook bytes"], "contacts.xlsx", {
    type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  });
}

function renderWizard(onClose = vi.fn()) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <ImportWizard onClose={onClose} />
    </QueryClientProvider>,
  );
  return onClose;
}

function dialog() {
  return within(screen.getByRole("dialog"));
}

/** Walk from the dropzone to the review step with a valid mapping. */
async function reachReview(): Promise<void> {
  fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
    target: { files: [csvFile()] },
  });
  await screen.findByText(/3 columns/);
  fireEvent.click(dialog().getByRole("button", { name: "Continue" })); // → options
  fireEvent.click(dialog().getByRole("button", { name: "Continue" })); // → review
}

beforeEach(() => {
  posts.length = 0;
  inspection.value = {
    type: "import_inspection",
    headers: ["Phone Number", "Full Name"],
    sample_row: ["+14155550001", "Priya Sharma"],
    sheet_name: "Contacts",
    estimated_rows: 2,
    errors: [],
  };
  importProgress.value = { ...importProgress.value, status: "running", error_report_url: null };
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("ImportWizard", () => {
  it("opens on the upload step", () => {
    renderWizard();
    expect(screen.getByRole("dialog")).toHaveAttribute("aria-label", "Import contacts");
    expect(screen.getByText("Drop a CSV or Excel file here")).toBeInTheDocument();
    expect(dialog().getByRole("button", { name: "Continue" })).toBeDisabled();
  });

  it("refuses a file that is not CSV or XLSX", async () => {
    renderWizard();
    fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
      target: { files: [new File(["x"], "contacts.xls", { type: "application/vnd.ms-excel" })] },
    });
    expect(await screen.findByRole("alert")).toHaveTextContent(/Choose a CSV or Excel/);
  });

  it("auto-maps the columns it recognises and leaves the rest alone", async () => {
    renderWizard();
    fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
      target: { files: [csvFile()] },
    });

    expect(await screen.findByLabelText("Map column Phone Number")).toHaveValue("phone_e164");
    expect(screen.getByLabelText("Map column Full Name")).toHaveValue("full_name");
    expect(screen.getByLabelText("Map column Loyalty tier")).toHaveValue("");
    // The first data row is shown under each column as a sample.
    expect(screen.getByText("+14155550001")).toBeInTheDocument();
  });

  it("blocks the mapping step until a phone column is chosen", async () => {
    renderWizard();
    fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
      target: { files: [csvFile("c.csv", "Name,Tier\nPriya,gold\n")] },
    });

    await screen.findByLabelText("Map column Name");
    expect(dialog().getByRole("button", { name: "Continue" })).toBeDisabled();
    expect(screen.getByRole("alert")).toHaveTextContent(/Map one column to Phone/);

    fireEvent.change(screen.getByLabelText("Map column Name"), {
      target: { value: "phone_e164" },
    });
    expect(dialog().getByRole("button", { name: "Continue" })).toBeEnabled();
  });

  it("summarises the file before starting", async () => {
    renderWizard();
    await reachReview();

    expect(screen.getByText(/^contacts\.csv · \d+ B$/)).toBeInTheDocument();
    expect(screen.getByText("2 of 3")).toBeInTheDocument(); // columns imported
    expect(screen.getByText("Skip duplicates")).toBeInTheDocument();
    const rows = screen.getByText("Rows").parentElement;
    expect(within(rows!).getByText("2")).toBeInTheDocument(); // counted locally
  });

  it("uploads the file, then starts the import with the mapping the API expects", async () => {
    renderWizard();
    await reachReview();
    fireEvent.click(dialog().getByRole("button", { name: "Start import" }));

    await waitFor(() => expect(posts).toHaveLength(2));
    expect(posts[0]?.path).toBe("/api/v1/media/upload");
    expect(posts[0]?.body).toMatchObject({ media_type: "document" });
    expect(posts[1]).toEqual({
      path: "/api/v1/contacts/import",
      body: {
        upload_id: "media-1",
        format: "csv",
        mapping: { "Phone Number": "phone_e164", "Full Name": "full_name" },
        dedup_strategy: "skip",
      },
    });
  });

  it("carries the chosen duplicate strategy", async () => {
    renderWizard();
    fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
      target: { files: [csvFile()] },
    });
    await screen.findByText(/3 columns/);
    fireEvent.click(dialog().getByRole("button", { name: "Continue" }));
    fireEvent.click(screen.getByRole("radio", { name: /Overwrite/ }));
    fireEvent.click(dialog().getByRole("button", { name: "Continue" }));
    fireEvent.click(dialog().getByRole("button", { name: "Start import" }));

    await waitFor(() => expect(posts).toHaveLength(2));
    expect(posts[1]?.body).toMatchObject({ dedup_strategy: "overwrite" });
  });

  it("shows live progress and then the partial-success result", async () => {
    importProgress.value = {
      ...importProgress.value,
      status: "partial_success",
      processed_rows: 2,
      success_rows: 1,
      error_rows: 1,
      error_report_url: "/api/v1/jobs/i1/errors.csv",
    };
    renderWizard();
    await reachReview();
    fireEvent.click(dialog().getByRole("button", { name: "Start import" }));

    expect(await screen.findByText("Finished with errors")).toBeInTheDocument();
    expect(screen.getByText(/1 contacts · 1 rows failed/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download error report" })).toHaveAttribute(
      "href",
      "/api/v1/jobs/i1/errors.csv",
    );
    fireEvent.click(screen.getByRole("button", { name: "Done" }));
  });

  it("guards the exit once a file is loaded", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
    const onClose = renderWizard();
    fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
      target: { files: [csvFile()] },
    });
    await screen.findByText(/3 columns/);

    fireEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(confirmSpy).toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();

    confirmSpy.mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "Close dialog" }));
    expect(onClose).toHaveBeenCalled();
  });

  it("inspects XLSX with the backend parser and reuses that upload for the import", async () => {
    renderWizard();
    fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
      target: { files: [xlsxFile()] },
    });

    expect(await screen.findByText(/2 columns/)).toBeInTheDocument();
    expect(screen.getByText("+14155550001")).toBeInTheDocument();
    expect(posts.map((call) => call.path)).toEqual([
      "/api/v1/media/upload",
      "/api/v1/contacts/import/inspect",
    ]);
    expect(posts[1]?.body).toEqual({ upload_id: "media-1", format: "xlsx" });

    fireEvent.click(dialog().getByRole("button", { name: "Continue" }));
    fireEvent.click(dialog().getByRole("button", { name: "Continue" }));
    expect(screen.getByText("Contacts")).toBeInTheDocument();
    expect(screen.getByText("About 2")).toBeInTheDocument();
    fireEvent.click(dialog().getByRole("button", { name: "Start import" }));

    await waitFor(() => expect(posts).toHaveLength(3));
    expect(posts[2]).toEqual({
      path: "/api/v1/contacts/import",
      body: {
        upload_id: "media-1",
        format: "xlsx",
        mapping: { "Phone Number": "phone_e164", "Full Name": "full_name" },
        dedup_strategy: "skip",
      },
    });
  });

  it("shows workbook header validation returned by inspection", async () => {
    inspection.value = {
      ...inspection.value,
      errors: [
        {
          field: "headers",
          code: "duplicate",
          message: "Repeated column names: Phone.",
        },
      ],
    };
    renderWizard();
    fireEvent.change(screen.getByLabelText("Choose a CSV or Excel file"), {
      target: { files: [xlsxFile()] },
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("Repeated column names: Phone.");
    expect(dialog().getByRole("button", { name: "Continue" })).toBeDisabled();
  });
});
