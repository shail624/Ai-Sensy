import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { InterventionActions } from "@/features/inbox/InterventionActions";
import type { Conversation } from "@/features/inbox/types";

const state = vi.hoisted(() => ({
  canWrite: true,
  intervene: vi.fn(),
  resolve: vi.fn(),
}));

vi.mock("@/lib/auth", () => ({ useHasPermission: () => state.canWrite }));
vi.mock("@/features/inbox/api", () => ({
  apiErrorMessage: () => "Could not change intervention",
  useInterveneConversation: () => ({ mutate: state.intervene, isPending: false, error: null }),
  useResolveIntervention: () => ({ mutate: state.resolve, isPending: false, error: null }),
}));

function conversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: "conv-1",
    status: "pending",
    assigned_to: null,
    ...overrides,
  } as Conversation;
}

describe("InterventionActions", () => {
  beforeEach(() => {
    state.canWrite = true;
    state.intervene.mockReset();
    state.resolve.mockReset();
  });

  it("lets the current agent intervene in a requested chat", () => {
    render(<InterventionActions conversation={conversation()} currentUserId="agent-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Intervene" }));
    expect(state.intervene).toHaveBeenCalledWith(undefined);
  });

  it("protects a requested chat already owned by another agent", () => {
    render(
      <InterventionActions
        conversation={conversation({ assigned_to: "agent-2" })}
        currentUserId="agent-1"
      />,
    );
    expect(screen.getByText("Owned by another agent")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Intervene" })).not.toBeInTheDocument();
  });

  it("lets the intervening agent resolve the active chat", () => {
    render(
      <InterventionActions
        conversation={conversation({ status: "open", assigned_to: "agent-1" })}
        currentUserId="agent-1"
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Resolve" }));
    expect(state.resolve).toHaveBeenCalledWith(undefined);
  });

  it("does not expose another agent's resolve action", () => {
    const { container } = render(
      <InterventionActions
        conversation={conversation({ status: "open", assigned_to: "agent-2" })}
        currentUserId="agent-1"
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("honors the inbox write permission", () => {
    state.canWrite = false;
    const { container } = render(
      <InterventionActions conversation={conversation()} currentUserId="agent-1" />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
