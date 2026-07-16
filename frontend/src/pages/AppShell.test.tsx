import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ThemeProvider } from "@/lib/theme";
import { AppShell } from "@/pages/AppShell";

// Foundation smoke test: the shell renders inside the theme provider (Doc 10 §11).
describe("AppShell", () => {
  it("renders the application heading", () => {
    render(
      <ThemeProvider>
        <AppShell />
      </ThemeProvider>,
    );
    expect(
      screen.getByRole("heading", { name: /WhatsApp Business Platform/i }),
    ).toBeInTheDocument();
  });

  it("exposes an accessible theme toggle", () => {
    render(
      <ThemeProvider>
        <AppShell />
      </ThemeProvider>,
    );
    expect(screen.getByLabelText(/toggle color theme/i)).toBeInTheDocument();
  });
});
