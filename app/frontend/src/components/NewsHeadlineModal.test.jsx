import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NewsHeadlineModal } from "./NewsHeadlineModal";

const SAMPLE_ITEM = {
  title: "Port strike disrupts shipping",
  link: "https://example.com/1",
  source: "BBC",
  summary: "Dock workers walk out at major ports.",
  published_at: "2026-08-05T12:00:00Z",
};

describe("NewsHeadlineModal", () => {
  beforeEach(() => {
    vi.spyOn(window, "open").mockImplementation(() => null);
  });

  it("shows headline details and action buttons", () => {
    render(<NewsHeadlineModal item={SAMPLE_ITEM} onClose={vi.fn()} onCreateScenario={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: /Port strike disrupts shipping/i })).toBeInTheDocument();
    expect(screen.getByText(/Dock workers walk out at major ports/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Read article/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /Create scenario/i })).toBeInTheDocument();
  });

  it("opens the article in a new tab when Read article is clicked", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<NewsHeadlineModal item={SAMPLE_ITEM} onClose={onClose} onCreateScenario={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /Read article/i }));

    expect(window.open).toHaveBeenCalledWith("https://example.com/1", "_blank", "noopener,noreferrer");
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onCreateScenario with the item when Create scenario is clicked", async () => {
    const user = userEvent.setup();
    const onCreateScenario = vi.fn();
    const onClose = vi.fn();
    render(
      <NewsHeadlineModal item={SAMPLE_ITEM} onClose={onClose} onCreateScenario={onCreateScenario} />,
    );

    await user.click(screen.getByRole("button", { name: /Create scenario/i }));

    expect(onCreateScenario).toHaveBeenCalledWith(SAMPLE_ITEM);
    expect(onClose).toHaveBeenCalled();
  });

  it("disables Read article when no link is available", () => {
    render(
      <NewsHeadlineModal
        item={{ ...SAMPLE_ITEM, link: "" }}
        onClose={vi.fn()}
        onCreateScenario={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: /Read article/i })).toBeDisabled();
  });
});
