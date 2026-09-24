import { fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

const sendText = vi.fn();
const sendFile = vi.fn();

vi.mock("@/features/inbox/api", () => ({
  apiErrorMessage: () => "error",
  useQuickReplies: () => ({ data: [] }),
  useSendMessage: () => ({ mutate: sendText, isPending: false, error: null }),
  useSendAttachment: () => ({ mutate: sendFile, isPending: false, error: null, reset: vi.fn() }),
  useSendLocation: () => ({ mutate: vi.fn(), isPending: false, error: null }),
  useTypingSignal: () => () => undefined,
}));
vi.mock("@/features/whatsapp-qr/api", () => ({
  useWhatsAppQrStatus: () => ({ isLoading: false, data: { connected: true } }),
}));
vi.mock("@/lib/auth", () => ({ useHasPermission: () => true }));

import { classifyFile } from "./AttachmentPreview";
import { MessageComposer } from "./MessageComposer";

const conversation = {
  id: "conv-1",
  connector_type: "waha",
  contact: { id: "c", name: "Shailesh", phone: "+919891000010" },
  window: { is_open: false },
} as never;

function renderComposer() {
  return render(
    <MemoryRouter>
      <MessageComposer conversation={conversation} />
    </MemoryRouter>,
  );
}

function file(name: string, type: string, size = 1000): File {
  const blob = new File(["x"], name, { type });
  Object.defineProperty(blob, "size", { value: size });
  return blob;
}

describe("classifyFile", () => {
  it("sorts files into WhatsApp kinds and refuses what WhatsApp would", () => {
    expect(classifyFile(file("a.jpg", "image/jpeg"))).toEqual({ kind: "image" });
    expect(classifyFile(file("a.mp4", "video/mp4"))).toEqual({ kind: "video" });
    expect(classifyFile(file("a.mp3", "audio/mpeg"))).toEqual({ kind: "audio" });
    expect(classifyFile(file("a.pdf", "application/pdf"))).toEqual({ kind: "document" });
    expect(classifyFile(file("a.exe", "application/x-msdownload"))).toHaveProperty("error");
    expect(classifyFile(file("big.jpg", "image/jpeg", 6 * 1024 * 1024))).toHaveProperty("error");
  });
});

describe("MessageComposer attachments and emoji", () => {
  beforeEach(() => {
    sendText.mockReset();
    sendFile.mockReset();
  });

  it("sends a chosen file with the typed text as its caption", () => {
    renderComposer();
    const pdf = file("plan.pdf", "application/pdf");
    fireEvent.change(screen.getByLabelText("Choose a file"), { target: { files: [pdf] } });
    expect(screen.getByText("plan.pdf")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Your plan" } });
    fireEvent.click(screen.getByRole("button", { name: "Send" }));

    expect(sendFile).toHaveBeenCalledWith({ file: pdf, kind: "document", caption: "Your plan" }, expect.anything());
    expect(sendText).not.toHaveBeenCalled();
  });

  it("explains a file WhatsApp cannot take instead of uploading it", () => {
    renderComposer();
    fireEvent.change(screen.getByLabelText("Choose a file"), { target: { files: [file("a.zip", "application/zip")] } });
    expect(screen.getByRole("alert")).toHaveTextContent("cannot be sent on WhatsApp");
    fireEvent.click(screen.getByRole("button", { name: "Send" }));
    expect(sendFile).not.toHaveBeenCalled();
  });

  it("inserts an emoji into the message", () => {
    renderComposer();
    fireEvent.change(screen.getByLabelText("Message"), { target: { value: "Hi " } });
    fireEvent.click(screen.getByRole("button", { name: "Emoji" }));
    fireEvent.click(screen.getByTitle("Gestures"));
    fireEvent.click(screen.getByRole("button", { name: "Insert 🙏" }));
    expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe("Hi 🙏");
  });

  it("offers photos, documents and audio from the attach menu", () => {
    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Attach a file" }));
    expect(screen.getByRole("menuitem", { name: /Photos & videos/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Document/ })).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: /Audio/ })).toBeInTheDocument();
  });
});

describe("parseCoordinates", () => {
  it("reads coordinates from what agents paste", async () => {
    const { parseCoordinates } = await import("./LocationDialog");
    expect(parseCoordinates("28.6139, 77.2090")).toEqual({ latitude: 28.6139, longitude: 77.209 });
    expect(parseCoordinates("https://www.google.com/maps/place/X/@28.63,77.21,17z")).toEqual({ latitude: 28.63, longitude: 77.21 });
    expect(parseCoordinates("https://maps.google.com/?q=19.07,72.87")).toEqual({ latitude: 19.07, longitude: 72.87 });
    expect(parseCoordinates("https://www.google.com/maps/place/Y/data=!3d12.97!4d77.59")).toEqual({ latitude: 12.97, longitude: 77.59 });
    expect(parseCoordinates("Connaught Place")).toBeNull();
    expect(parseCoordinates("99, 200")).toBeNull();
  });
});
