import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { NewsTicker } from "./NewsTicker";

const SAMPLE_ITEM = {
  title: "Port strike disrupts shipping",
  link: "https://example.com/1",
  source: "BBC",
  summary: "Dock workers walk out at major ports.",
  published_at: "2026-08-05T12:00:00Z",
};

describe("NewsTicker", () => {
  it("renders headlines with globe icons as headline buttons", () => {
    render(<NewsTicker items={[SAMPLE_ITEM]} />);
    const buttons = screen.getAllByRole("button", {
      name: /News headline: BBC: Port strike disrupts shipping/i,
    });
    expect(buttons.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("News")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "About supply chain news" })).toBeInTheDocument();
  });

  it("opens the headline modal when a headline is clicked", async () => {
    const user = userEvent.setup();
    render(<NewsTicker items={[SAMPLE_ITEM]} onCreateScenarioFromNews={vi.fn()} />);

    await user.click(
      screen.getAllByRole("button", {
        name: /News headline: BBC: Port strike disrupts shipping/i,
      })[0],
    );

    expect(screen.getByRole("dialog", { name: /Port strike disrupts shipping/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Read article/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Create scenario/i })).toBeInTheDocument();
  });

  it("calls onCreateScenarioFromNews when Create scenario is chosen in the modal", async () => {
    const user = userEvent.setup();
    const onCreateScenarioFromNews = vi.fn();
    render(
      <NewsTicker items={[SAMPLE_ITEM]} onCreateScenarioFromNews={onCreateScenarioFromNews} />,
    );

    await user.click(
      screen.getAllByRole("button", {
        name: /News headline: BBC: Port strike disrupts shipping/i,
      })[0],
    );
    await user.click(screen.getByRole("button", { name: /Create scenario/i }));

    expect(onCreateScenarioFromNews).toHaveBeenCalledWith(SAMPLE_ITEM);
    expect(screen.queryByRole("dialog", { name: /Port strike disrupts shipping/i })).not.toBeInTheDocument();
  });

  it("shows quiet empty state when there are no headlines", () => {
    render(<NewsTicker items={[]} loading={false} />);
    expect(screen.getByText(/No headlines available/i)).toBeInTheDocument();
  });

  it("shows loading text while waiting for first fetch", () => {
    render(<NewsTicker items={[]} loading={true} />);
    expect(screen.getAllByText(/Loading latest headlines/i).length).toBeGreaterThan(0);
  });
});
