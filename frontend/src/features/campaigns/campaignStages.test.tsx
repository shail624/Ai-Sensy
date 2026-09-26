import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CampaignStageBar, stageIndexFor } from "./CampaignStageBar";

describe("Campaign stages (reference layout)", () => {
  it("groups the wizard's steps into the three reference stages", () => {
    expect(stageIndexFor("audience")).toBe(0);
    expect(stageIndexFor("basics")).toBe(1);
    expect(stageIndexFor("preview")).toBe(1);
    expect(stageIndexFor("delivery")).toBe(2);
    expect(stageIndexFor("review")).toBe(2);
  });

  it("marks the current stage", () => {
    render(<CampaignStageBar step="preview" />);
    expect(screen.getByText("Create Message").closest("[role=listitem]")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("Campaign Details").closest("[role=listitem]")).not.toHaveAttribute("aria-current");
  });
});
