import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { DashboardHeader } from "./DashboardHeader";

describe("DashboardHeader", () => {
  it("calls onNavigate when nav buttons are used", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    const onToggleTheme = vi.fn();
    render(
      <DashboardHeader
        isLightTheme={false}
        onToggleTheme={onToggleTheme}
        activeView="simulation"
        onNavigate={onNavigate}
      />,
    );
    await user.click(screen.getByRole("button", { name: /knowledge bases/i }));
    expect(onNavigate).toHaveBeenCalledWith("knowledge-bases");
    await user.click(screen.getByRole("button", { name: /^simulation$/i }));
    expect(onNavigate).toHaveBeenCalledWith("simulation");
    expect(screen.queryByRole("button", { name: /^dashboard$/i })).not.toBeInTheDocument();
  });

  it("toggles theme from the theme control", async () => {
    const user = userEvent.setup();
    const onToggleTheme = vi.fn();
    render(<DashboardHeader isLightTheme={false} onToggleTheme={onToggleTheme} />);
    await user.click(screen.getByRole("button", { name: /toggle theme/i }));
    expect(onToggleTheme).toHaveBeenCalled();
  });

  it("shows the build/version indicator so a running container can be verified", () => {
    render(<DashboardHeader isLightTheme={false} onToggleTheme={vi.fn()} />);
    // Local/test runs have no VITE_GIT_COMMIT baked in, so this falls back to "dev".
    expect(screen.getByText(/dev/i)).toBeInTheDocument();
  });
});
