import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const state = { url: null as string | null, loading: true, failed: false };
vi.mock("@/features/inbox/api", () => ({ useMessageMedia: () => state }));

import { MessageMedia } from "./MessageMedia";

describe("MessageMedia", () => {
  it("shows a photo once it has loaded", () => {
    state.url = "blob:photo";
    render(<MessageMedia messageId="m1" media={{ kind: "image", caption: "bill", filename: null, mimeType: "image/jpeg", link: null }} />);
    expect(screen.getByRole("img", { name: "bill" })).toHaveAttribute("src", "blob:photo");
  });

  it("plays video and audio in the chat", () => {
    state.url = "blob:clip";
    const { container, rerender } = render(<MessageMedia messageId="m2" media={{ kind: "video", caption: null, filename: null, mimeType: "video/mp4", link: null }} />);
    expect(container.querySelector("video")).toHaveAttribute("src", "blob:clip");
    rerender(<MessageMedia messageId="m3" media={{ kind: "audio", caption: null, filename: null, mimeType: "audio/ogg", link: null }} />);
    expect(container.querySelector("audio")).toHaveAttribute("src", "blob:clip");
  });

  it("offers a document for download", () => {
    state.url = "blob:doc";
    render(<MessageMedia messageId="m4" media={{ kind: "document", caption: null, filename: "plan.pdf", mimeType: "application/pdf", link: null }} />);
    expect(screen.getByRole("link", { name: "Download plan.pdf" })).toHaveAttribute("download", "plan.pdf");
  });

  it("says when a file cannot be shown", () => {
    state.url = null;
    state.failed = true;
    render(<MessageMedia messageId="m5" media={{ kind: "image", caption: null, filename: null, mimeType: null, link: null }} />);
    expect(screen.getByText("File not available")).toBeInTheDocument();
  });
});
