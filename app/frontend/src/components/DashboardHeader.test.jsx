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
        activeView="dashboard"
        onNavigate={onNavigate}
      />
    );
    await user.click(screen.getByRole("button", { name: /knowledge bases/i }));
    expect(onNavigate).toHaveBeenCalledWith("knowledge-bases");
    await user.click(screen.getByRole("button", { name: /^dashboard$/i }));
    expect(onNavigate).toHaveBeenCalledWith("dashboard");
  });

  it("toggles theme from the theme control", async () => {
    const user = userEvent.setup();
    const onToggleTheme = vi.fn();
    render(<DashboardHeader isLightTheme={false} onToggleTheme={onToggleTheme} />);
    await user.click(screen.getByRole("button", { name: "☀️" }));
    expect(onToggleTheme).toHaveBeenCalled();
  });
});
