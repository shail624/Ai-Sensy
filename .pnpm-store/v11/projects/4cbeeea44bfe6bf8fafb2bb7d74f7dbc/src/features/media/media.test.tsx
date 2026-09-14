import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MediaActions } from "@/features/media/MediaActions";
import { MediaTypeChip, UsageChip } from "@/features/media/MediaBadges";
import { MediaFilters } from "@/features/media/MediaFilters";
import { MediaRenderer } from "@/features/media/MediaPreview";
import { MediaTable } from "@/features/media/MediaTable";
import { MediaUploadDialog } from "@/features/media/MediaUploadDialog";
import {
  displayName,
  filterMedia,
  formatLimit,
  librarySummary,
  matchesSearch,
  mediaTypeForMime,
  PAGE_SIZE,
  selectMediaPage,
  sortMedia,
  validateUpload,
} from "@/features/media/selectors";
import type { MediaAsset, MediaListQuery } from "@/features/media/types";
import { acceptFor, DEFAULT_LIST_QUERY, isDeletable, MEDIA_RULES } from "@/features/media/types";
import { formatBytes, formatDuration, UNKNOWN } from "@/lib/format";

// Permission-gated actions read the session; the roster is swapped per test.
const permissions = { value: ["media:read", "media:write"] };
vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    status: "authenticated",
    user: { id: "u1", permissions: permissions.value, is_superuser: false },
    login: vi.fn(),
    logout: vi.fn(),
    hasPermission: (code: string) => permissions.value.includes(code),
  }),
  useHasPermission: (code: string) => permissions.value.includes(code),
}));

// Keep the tests hermetic: no component here is being tested for what it fetches, and a real
// request would only add a failed connection per render.
vi.mock("@/lib/api/client", () => {
  const nothing = async () => ({ error: new Error("network disabled under test") });
  return {
    api: { GET: nothing, POST: nothing, PATCH: nothing, DELETE: nothing },
    authClient: { POST: nothing },
    setSessionExpiredHandler: vi.fn(),
    refreshOnce: vi.fn(),
  };
});

const MB = 1024 * 1024;

function assetFixture(overrides: Partial<MediaAsset> = {}): MediaAsset {
  return {
    id: "m1",
    type: "media_asset",
    media_type: "image",
    mime_type: "image/png",
    file_name: "promo-banner.png",
    byte_size: 2 * MB,
    sha256: "abc123def4567890abc123def4567890abc123def4567890abc123def4567890",
    storage_backend: "local",
    width: 1200,
    height: 628,
    duration_sec: null,
    usage_count: 0,
    created_at: "2026-07-20T10:00:00Z",
    ...overrides,
  };
}

function query(overrides: Partial<MediaListQuery> = {}): MediaListQuery {
  return { ...DEFAULT_LIST_QUERY, ...overrides };
}

function fileFixture(name: string, type: string, size: number): File {
  const file = new File(["x"], name, { type });
  // `File` computes size from its parts; the tests need specific sizes without allocating them.
  Object.defineProperty(file, "size", { value: size });
  return file;
}

function withProviders(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  permissions.value = ["media:read", "media:write"];
});

describe("selectors — naming and search", () => {
  it("falls back to a stable name when the file has none", () => {
    expect(displayName(assetFixture())).toBe("promo-banner.png");
    expect(displayName(assetFixture({ file_name: null }))).toBe("image-abc123def456");
  });

  it("matches the file name case-insensitively", () => {
    expect(matchesSearch(assetFixture(), "BANNER")).toBe(true);
    expect(matchesSearch(assetFixture(), "invoice")).toBe(false);
    expect(matchesSearch(assetFixture(), "  ")).toBe(true);
  });

  it("also matches an id or hash prefix, which is what an operator usually has", () => {
    expect(matchesSearch(assetFixture(), "abc123")).toBe(true);
    expect(matchesSearch(assetFixture(), "m1")).toBe(true);
    // A mid-hash fragment is not a prefix and should not match.
    expect(matchesSearch(assetFixture(), "def4567890abc")).toBe(false);
  });
});

describe("selectors — filtering, sorting, pagination", () => {
  const rows = [
    assetFixture({ id: "a", file_name: "alpha.png", media_type: "image", byte_size: 100, created_at: "2026-07-01T00:00:00Z" }),
    assetFixture({ id: "b", file_name: "bravo.pdf", media_type: "document", byte_size: 900, created_at: "2026-07-02T00:00:00Z" }),
    assetFixture({ id: "c", file_name: "charlie.mp4", media_type: "video", byte_size: 500, created_at: "2026-07-03T00:00:00Z" }),
  ];

  it("filters by media type", () => {
    expect(filterMedia(rows, query({ mediaType: "video" })).map((r) => r.id)).toEqual(["c"]);
  });

  it("combines search and type conjunctively", () => {
    expect(filterMedia(rows, query({ q: "alpha", mediaType: "document" }))).toHaveLength(0);
  });

  it("sorts by date, name and size without mutating the input", () => {
    const before = rows.map((row) => row.id);
    expect(sortMedia(rows, "-created_at").map((r) => r.id)).toEqual(["c", "b", "a"]);
    expect(sortMedia(rows, "name").map((r) => r.id)).toEqual(["a", "b", "c"]);
    expect(sortMedia(rows, "-byte_size").map((r) => r.id)).toEqual(["b", "c", "a"]);
    expect(sortMedia(rows, "byte_size").map((r) => r.id)).toEqual(["a", "c", "b"]);
    expect(rows.map((row) => row.id)).toEqual(before);
  });

  it("reports page counts over the filtered set and clamps a dead page", () => {
    expect(selectMediaPage(rows, query({ mediaType: "image" })).total).toBe(1);
    expect(selectMediaPage(rows, query({ page: 9 })).page).toBe(1);
  });

  it("slices at the page size", () => {
    const many = Array.from({ length: PAGE_SIZE + 4 }, (_, index) =>
      assetFixture({ id: `m${index}`, file_name: `file-${index}.png` }),
    );
    expect(selectMediaPage(many, query()).rows).toHaveLength(PAGE_SIZE);
    expect(selectMediaPage(many, query({ page: 2 })).rows).toHaveLength(4);
  });

  it("summarises the library by count, bytes and what is still deletable", () => {
    const summary = librarySummary([
      assetFixture({ byte_size: 1000, usage_count: 0 }),
      assetFixture({ byte_size: 2000, usage_count: 3 }),
    ]);
    expect(summary).toEqual({ count: 2, bytes: 3000, unused: 1 });
  });
});

describe("selectors — upload validation", () => {
  it("asks for the media type first, because every other rule depends on it", () => {
    expect(validateUpload(null, "")).toMatchObject({ field: "media_type" });
  });

  it("requires a non-empty file", () => {
    expect(validateUpload(null, "image")).toMatchObject({ field: "file" });
    expect(validateUpload(fileFixture("a.png", "image/png", 0), "image")?.message).toMatch(/empty/);
  });

  it("refuses a MIME type the media type does not allow", () => {
    const problem = validateUpload(fileFixture("a.gif", "image/gif", 100), "image");
    expect(problem?.message).toMatch(/image\/gif is not allowed/);
  });

  it("refuses a file over the ceiling for its type", () => {
    // The image ceiling is 5 MB; one byte over must fail, and exactly at it must pass.
    expect(validateUpload(fileFixture("a.png", "image/png", 5 * MB + 1), "image")?.message).toMatch(
      /larger than the 5 MB limit/,
    );
    expect(validateUpload(fileFixture("a.png", "image/png", 5 * MB), "image")).toBeNull();
  });

  it("leaves the decision to the server when the browser reports no MIME type", () => {
    expect(validateUpload(fileFixture("mystery", "", 100), "document")).toBeNull();
  });

  it("applies each media type's own ceiling", () => {
    expect(validateUpload(fileFixture("s.webp", "image/webp", 600 * 1024), "sticker")?.message).toMatch(
      /500 KB limit/,
    );
    expect(validateUpload(fileFixture("v.mp4", "video/mp4", 10 * MB), "video")).toBeNull();
  });

  it("renders limits the way the rule is written", () => {
    expect(formatLimit(MEDIA_RULES.image.maxBytes)).toBe("5 MB");
    expect(formatLimit(MEDIA_RULES.sticker.maxBytes)).toBe("500 KB");
  });

  it("maps a MIME type back to the one media type that claims it", () => {
    expect(mediaTypeForMime("image/png")).toBe("image");
    expect(mediaTypeForMime("image/webp")).toBe("sticker");
    expect(mediaTypeForMime("application/pdf")).toBe("document");
    expect(mediaTypeForMime("image/gif")).toBeNull();
  });

  it("builds the file picker's accept list from the same rules", () => {
    expect(acceptFor("image")).toBe("image/jpeg,image/png");
  });
});

describe("types — deletability", () => {
  it("mirrors the server's guard: an asset that has been used cannot be deleted", () => {
    expect(isDeletable(assetFixture({ usage_count: 0 }))).toBe(true);
    expect(isDeletable(assetFixture({ usage_count: 1 }))).toBe(false);
  });
});

describe("lib/format — sizes and durations", () => {
  it("uses binary units, so a file at the limit does not read as over it", () => {
    expect(formatBytes(5 * MB)).toBe("5.0 MB");
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(null)).toBe(UNKNOWN);
  });

  it("formats durations as m:ss, widening past an hour", () => {
    expect(formatDuration(9)).toBe("0:09");
    expect(formatDuration(75)).toBe("1:15");
    expect(formatDuration(3725)).toBe("1:02:05");
    expect(formatDuration(null)).toBe(UNKNOWN);
  });
});

describe("MediaBadges", () => {
  it("labels known media types and passes unknown ones through verbatim", () => {
    withProviders(
      <>
        <MediaTypeChip value="document" />
        <MediaTypeChip value="hologram" />
      </>,
    );
    expect(screen.getByText("Document")).toBeInTheDocument();
    expect(screen.getByText("hologram")).toBeInTheDocument();
  });

  it("calls an unused asset unused, because that is the state it can be deleted in", () => {
    withProviders(<UsageChip count={0} />);
    expect(screen.getByText("Unused")).toBeInTheDocument();
  });

  it("pluralises the usage count", () => {
    withProviders(<UsageChip count={1} />);
    expect(screen.getByText("Used in 1 message")).toBeInTheDocument();
  });
});

describe("MediaRenderer", () => {
  it("renders an image with the file name as its alt text", () => {
    withProviders(<MediaRenderer asset={assetFixture()} url="/signed/a.png" />);
    const image = screen.getByAltText("promo-banner.png");
    expect(image).toHaveAttribute("src", "/signed/a.png");
  });

  it("renders a sticker as an image too", () => {
    withProviders(
      <MediaRenderer
        asset={assetFixture({ media_type: "sticker", mime_type: "image/webp", file_name: "s.webp" })}
        url="/signed/s.webp"
      />,
    );
    expect(screen.getByAltText("s.webp")).toBeInTheDocument();
  });

  it("gives video and audio native controls", () => {
    const { container } = withProviders(
      <MediaRenderer
        asset={assetFixture({ media_type: "video", mime_type: "video/mp4" })}
        url="/signed/v.mp4"
      />,
    );
    const video = container.querySelector("video");
    expect(video).toHaveAttribute("src", "/signed/v.mp4");
    expect(video).toHaveAttribute("controls");

    const audio = withProviders(
      <MediaRenderer
        asset={assetFixture({ media_type: "audio", mime_type: "audio/mpeg" })}
        url="/signed/a.mp3"
      />,
    ).container.querySelector("audio");
    expect(audio).toHaveAttribute("controls");
  });

  it("embeds a PDF inline", () => {
    const { container } = withProviders(
      <MediaRenderer
        asset={assetFixture({ media_type: "document", mime_type: "application/pdf" })}
        url="/signed/d.pdf"
      />,
    );
    expect(container.querySelector("object")).toHaveAttribute("data", "/signed/d.pdf");
  });

  it("offers a download instead of a viewer for a document browsers cannot show", () => {
    withProviders(
      <MediaRenderer
        asset={assetFixture({ media_type: "document", mime_type: "text/csv", file_name: "rows.csv" })}
        url="/signed/rows.csv"
      />,
    );
    expect(screen.getByText(/cannot be previewed in a browser/)).toBeInTheDocument();
  });
});

describe("MediaTable", () => {
  it("renders an asset with its size and a link to its detail page", () => {
    withProviders(<MediaTable assets={[assetFixture()]} showPreviews={false} />);
    expect(screen.getByRole("link", { name: "promo-banner.png" })).toHaveAttribute(
      "href",
      "/media/m1",
    );
    expect(screen.getByText("2.0 MB")).toBeInTheDocument();
    expect(screen.getByText("1200×628")).toBeInTheDocument();
  });

  it("shows a duration where an asset has no dimensions", () => {
    withProviders(
      <MediaTable
        assets={[
          assetFixture({ media_type: "audio", width: null, height: null, duration_sec: 95 }),
        ]}
        showPreviews={false}
      />,
    );
    expect(screen.getByText("1:35")).toBeInTheDocument();
  });

  it("renders a glyph rather than fetching bytes while previews are off", () => {
    const { container } = withProviders(
      <MediaTable assets={[assetFixture()]} showPreviews={false} />,
    );
    expect(container.querySelector("img")).toBeNull();
  });
});

describe("MediaFilters", () => {
  it("returns to the first page whenever a filter changes", () => {
    const onChange = vi.fn();
    withProviders(<MediaFilters filters={query({ page: 4 })} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Type"), { target: { value: "video" } });
    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ mediaType: "video", page: 1 }));
  });

  it("offers every media type", () => {
    withProviders(<MediaFilters filters={query()} onChange={vi.fn()} />);
    const select = screen.getByLabelText("Type");
    expect(within(select).getByRole("option", { name: "Sticker" })).toBeInTheDocument();
  });
});

describe("MediaActions — permission and usage gating", () => {
  it("offers delete only while nothing has used the asset", () => {
    withProviders(<MediaActions asset={assetFixture({ usage_count: 0 })} compact />);
    expect(screen.getByRole("button", { name: "Delete" })).toBeInTheDocument();
  });

  it("explains why an in-use asset cannot be deleted instead of offering the button", () => {
    withProviders(<MediaActions asset={assetFixture({ usage_count: 2 })} compact />);
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.getByText("In use — cannot be deleted")).toBeInTheDocument();
  });

  it("hides every write control from a read-only user, but keeps Copy ID", () => {
    permissions.value = ["media:read"];
    withProviders(<MediaActions asset={assetFixture()} compact />);
    expect(screen.queryByRole("button", { name: "Delete" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copy ID" })).toBeInTheDocument();
  });

  it("offers download and replace only where there is room for them", () => {
    withProviders(<MediaActions asset={assetFixture()} compact />);
    expect(screen.queryByRole("button", { name: "Replace" })).not.toBeInTheDocument();

    withProviders(<MediaActions asset={assetFixture({ id: "m2" })} />);
    expect(screen.getByRole("button", { name: "Replace" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Download" })).toBeInTheDocument();
  });

  it("copies the media id to the clipboard", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });

    withProviders(<MediaActions asset={assetFixture()} compact />);
    fireEvent.click(screen.getByRole("button", { name: "Copy ID" }));
    expect(writeText).toHaveBeenCalledWith("m1");
    expect(await screen.findByRole("button", { name: "Copied" })).toBeInTheDocument();
  });

  it("confirms a delete before destroying the file", () => {
    withProviders(<MediaActions asset={assetFixture()} compact />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(
      within(screen.getByRole("dialog")).getByText(/promo-banner\.png/),
    ).toBeInTheDocument();
  });
});

describe("MediaUploadDialog", () => {
  it("reports the first validation problem rather than sending the file", () => {
    withProviders(<MediaUploadDialog onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: "Upload" }));
    expect(screen.getByText(/Choose what kind of file this is/)).toBeInTheDocument();
  });

  it("shows the ceiling and allowed types once a media type is chosen", () => {
    withProviders(<MediaUploadDialog onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Media type"), { target: { value: "image" } });
    expect(screen.getByText(/Up to 5 MB · image\/jpeg, image\/png/)).toBeInTheDocument();
  });

  it("preselects the media type from the chosen file", () => {
    withProviders(<MediaUploadDialog onClose={vi.fn()} />);
    const input = screen.getByLabelText("File") as HTMLInputElement;
    const file = fileFixture("clip.mp4", "video/mp4", 1000);
    fireEvent.change(input, { target: { files: [file] } });
    expect(screen.getByLabelText("Media type")).toHaveValue("video");
  });

  it("fixes the media type when replacing, because a replacement keeps its kind", () => {
    withProviders(<MediaUploadDialog replacing={assetFixture()} onClose={vi.fn()} />);
    expect(screen.getByLabelText("Media type")).toBeDisabled();
    expect(screen.getByLabelText("Media type")).toHaveValue("image");
    expect(screen.getByRole("button", { name: "Replace file" })).toBeInTheDocument();
  });

  it("refuses an over-size file at the picker", () => {
    withProviders(<MediaUploadDialog onClose={vi.fn()} />);
    fireEvent.change(screen.getByLabelText("Media type"), { target: { value: "image" } });
    fireEvent.change(screen.getByLabelText("File"), {
      target: { files: [fileFixture("huge.png", "image/png", 6 * MB)] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Upload" }));
    expect(screen.getByText(/larger than the 5 MB limit/)).toBeInTheDocument();
  });
});
