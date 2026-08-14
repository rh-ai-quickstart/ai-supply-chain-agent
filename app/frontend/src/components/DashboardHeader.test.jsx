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
    expect(screen.queryByRole("button", { name: /create scenario/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /live flights/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^dashboard$/i })).not.toBeInTheDocument();
  });

  it("marks the active view on the matching nav button", () => {
    render(
      <DashboardHeader
        isLightTheme={false}
        onToggleTheme={vi.fn()}
        activeView="knowledge-bases"
        onNavigate={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /knowledge bases/i })).toHaveClass(
      "dashboard-nav-btn--active",
    );
    expect(screen.getByRole("button", { name: /^simulation$/i })).not.toHaveClass(
      "dashboard-nav-btn--active",
    );
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

  it("shows the news ticker on the simulation view", () => {
    const item = {
      title: "Port strike disrupts shipping",
      link: "https://example.com/1",
      source: "BBC",
    };
    render(
      <DashboardHeader
        isLightTheme={false}
        onToggleTheme={vi.fn()}
        activeView="simulation"
        onNavigate={vi.fn()}
        newsItems={[item]}
        onCreateScenarioFromNews={vi.fn()}
      />,
    );
    expect(screen.getByRole("region", { name: /supply chain news ticker/i })).toBeInTheDocument();
    expect(screen.getByText("News")).toBeInTheDocument();
  });

  it("hides the news ticker on the knowledge bases view", () => {
    render(
      <DashboardHeader
        isLightTheme={false}
        onToggleTheme={vi.fn()}
        activeView="knowledge-bases"
        onNavigate={vi.fn()}
        newsItems={[{ title: "Headline", link: "https://example.com" }]}
      />,
    );
    expect(screen.queryByRole("region", { name: /supply chain news ticker/i })).not.toBeInTheDocument();
  });
});
